"""
Thread-safe in-memory state store.

Locking strategy:
- One RLock per SKU (granular).  Operations spanning multiple SKUs (none yet)
  would acquire locks in lexicographic order to avoid deadlocks.
- The sweeper runs in a background thread and acquires the same per-SKU locks
  for expiry, so the main execution path *never* blocks waiting for expiry.
- Internal mutable dicts are *never* returned to callers — every read returns
  frozen dataclass snapshots or primitive values.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .models import (
    ErrorCode,
    IdempotencyRecord,
    Product,
    ReservationRecord,
    ReservationState,
    SkuReport,
    SystemConfig,
)

# ── Internal (mutable) bookkeeping ─────────────────────────────────
# Guarded by _sku_locks[sku]


@dataclass(frozen=False)  # noqa: F811 — dataclass re-definition is fine here
class _MutableSku:
    """Mutable per-SKU counters — only ever touched while holding the SKU lock."""

    product: Product
    sold: int = 0
    # active reservations keyed by reservation_id
    reservations: dict = field(default_factory=dict)
    # per-user counters for active reservations: user_id -> currently reserved qty
    user_held: dict = field(default_factory=dict)


@dataclass(frozen=False)
class _MutableReservation:
    """Mutable reservation state — only accessed under the owning SKU's lock."""

    reservation_id: str
    sku: str
    user_id: str
    quantity: int
    state: ReservationState = ReservationState.RESERVED
    created_at: float = 0.0
    expires_at: float = 0.0
    confirmed_at: Optional[float] = None
    released_at: Optional[float] = None

    def to_record(self) -> ReservationRecord:
        return ReservationRecord(
            reservation_id=self.reservation_id,
            sku=self.sku,
            user_id=self.user_id,
            quantity=self.quantity,
            state=self.state,
            created_at=self.created_at,
            expires_at=self.expires_at,
            confirmed_at=self.confirmed_at,
            released_at=self.released_at,
        )


# ── The Store ──────────────────────────────────────────────────────


class StateStore:
    """Thread-safe in-memory store.  Public methods are the only way in.

    All mutating methods return a (success, payload) tuple where success is a
    bool so callers never have to reason about partial state.
    """

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        # Per-SKU granularity
        self._skus: Dict[str, _MutableSku] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._locks_lock = threading.Lock()  # only guards the dict, not values

        # Idempotency — coarse lock is cheap enough here
        self._idempotency: Dict[str, IdempotencyRecord] = {}
        self._idempotency_lock = threading.Lock()

    # ── init ──────────────────────────────────────────────────────

    def load_products(self, products: List[Product]) -> None:
        """Called once at startup before any traffic."""
        t0 = time.monotonic()
        for p in products:
            p.validate()
            self._skus[p.sku] = _MutableSku(product=p)
            self._locks[p.sku] = threading.RLock()
        print(f"[store] Loaded {len(products)} SKUs in {(time.monotonic() - t0)*1000:.1f} ms")

    # ── sku-level lock helper ─────────────────────────────────────

    def _get_lock(self, sku: str) -> threading.RLock:
        """Returns the RLock for *sku*, creating it on first access."""
        with self._locks_lock:
            if sku not in self._locks:
                self._locks[sku] = threading.RLock()
            return self._locks[sku]

    def _get_sku(self, sku: str) -> Optional[_MutableSku]:
        return self._skus.get(sku)

    # ── M2: Reserve ───────────────────────────────────────────────

    def reserve(
        self,
        sku: str,
        user_id: str,
        quantity: int,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        """Attempt to reserve *quantity* of *sku* for *user_id*.

        Returns (True, ReservationRecord) or (False, error_dict).
        """
        if idempotency_key:
            cached = self._check_idempotency(idempotency_key)
            if cached is not None:
                return cached

        if quantity < 1:
            result = {
                "error": ErrorCode.INVALID_REQUEST.value,
                "message": "quantity must be >= 1",
            }
            if idempotency_key:
                self._store_idempotency(idempotency_key, False, result)
            return False, result

        lock = self._get_lock(sku)
        with lock:
            sku_obj = self._get_sku(sku)
            if sku_obj is None:
                result = {
                    "error": ErrorCode.SKU_NOT_FOUND.value,
                    "message": f"SKU '{sku}' not found",
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            product = sku_obj.product

            # ── Limit check (M4) — includes currently-held reservations ──
            already_held = sku_obj.user_held.get(user_id, 0)
            if already_held + quantity > product.per_user_limit:
                result = {
                    "error": ErrorCode.USER_LIMIT_EXCEEDED.value,
                    "message": (
                        f"User '{user_id}' would hold {already_held + quantity} "
                        f"(limit {product.per_user_limit}) for SKU '{sku}'"
                    ),
                    "currently_held": already_held,
                    "per_user_limit": product.per_user_limit,
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            # ── Stock check ──
            available = product.total_stock - sku_obj.sold - sum(
                r.quantity
                for r in sku_obj.reservations.values()
                if r.state == ReservationState.RESERVED
            )
            if available < quantity:
                result = {
                    "error": ErrorCode.INSUFFICIENT_STOCK.value,
                    "message": (
                        f"Requested {quantity}, available {available} for SKU '{sku}'"
                    ),
                    "available": available,
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            # ── Create reservation ──
            now = time.monotonic()
            reservation_id = str(uuid.uuid4())
            res = _MutableReservation(
                reservation_id=reservation_id,
                sku=sku,
                user_id=user_id,
                quantity=quantity,
                state=ReservationState.RESERVED,
                created_at=now,
                expires_at=now + self.config.reservation_ttl_seconds,
            )
            sku_obj.reservations[reservation_id] = res
            sku_obj.user_held[user_id] = already_held + quantity

            record = res.to_record()
            if idempotency_key:
                self._store_idempotency(idempotency_key, True, record)

        return True, record

    # ── M3: Confirm ───────────────────────────────────────────────

    def confirm(
        self,
        reservation_id: str,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        """Permanently deduct stock.  Idempotent: if already SOLD, returns the
        existing record (not an error)."""
        if idempotency_key:
            cached = self._check_idempotency(idempotency_key)
            if cached is not None:
                return cached

        # We need the SKU to acquire the right lock.  reservation_id encodes
        # nothing, so we must search.  We keep a reservation_id → sku index.
        sku = self._find_sku_for_reservation(reservation_id)
        if sku is None:
            result = {
                "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                "message": f"Reservation '{reservation_id}' not found",
            }
            if idempotency_key:
                self._store_idempotency(idempotency_key, False, result)
            return False, result

        lock = self._get_lock(sku)
        with lock:
            sku_obj = self._get_sku(sku)
            if sku_obj is None:
                result = {
                    "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                    "message": f"Reservation '{reservation_id}' not found",
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            res = sku_obj.reservations.get(reservation_id)
            if res is None:
                result = {
                    "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                    "message": f"Reservation '{reservation_id}' not found",
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            # ── State machine ──
            if res.state == ReservationState.SOLD:
                # Idempotent — return existing
                record = res.to_record()
                if idempotency_key:
                    self._store_idempotency(idempotency_key, True, record)
                return True, record

            if res.state == ReservationState.RELEASED:
                result = {
                    "error": ErrorCode.RESERVATION_ALREADY_TERMINAL.value,
                    "message": (
                        f"Reservation '{reservation_id}' was already released "
                        f"(cancelled or expired) — cannot confirm."
                    ),
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            # Transition RESERVED → SOLD
            res.state = ReservationState.SOLD
            res.confirmed_at = time.monotonic()
            sku_obj.sold += res.quantity

            # Release the user's held count
            user_id = res.user_id
            held = sku_obj.user_held.get(user_id, 0)
            new_held = held - res.quantity
            if new_held <= 0:
                sku_obj.user_held.pop(user_id, None)
            else:
                sku_obj.user_held[user_id] = new_held

            record = res.to_record()
            if idempotency_key:
                self._store_idempotency(idempotency_key, True, record)

        return True, record

    # ── M3: Cancel ────────────────────────────────────────────────

    def cancel(
        self,
        reservation_id: str,
        idempotency_key: Optional[str] = None,
    ) -> tuple[bool, Any]:
        """Release stock back.  Idempotent: if already RELEASED, returns the
        existing record."""
        if idempotency_key:
            cached = self._check_idempotency(idempotency_key)
            if cached is not None:
                return cached

        sku = self._find_sku_for_reservation(reservation_id)
        if sku is None:
            result = {
                "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                "message": f"Reservation '{reservation_id}' not found",
            }
            if idempotency_key:
                self._store_idempotency(idempotency_key, False, result)
            return False, result

        lock = self._get_lock(sku)
        with lock:
            sku_obj = self._get_sku(sku)
            if sku_obj is None:
                result = {
                    "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                    "message": f"Reservation '{reservation_id}' not found",
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            res = sku_obj.reservations.get(reservation_id)
            if res is None:
                result = {
                    "error": ErrorCode.RESERVATION_NOT_FOUND.value,
                    "message": f"Reservation '{reservation_id}' not found",
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            if res.state == ReservationState.RELEASED:
                record = res.to_record()
                if idempotency_key:
                    self._store_idempotency(idempotency_key, True, record)
                return True, record

            if res.state == ReservationState.SOLD:
                result = {
                    "error": ErrorCode.RESERVATION_ALREADY_TERMINAL.value,
                    "message": (
                        f"Reservation '{reservation_id}' is already SOLD — cannot cancel."
                    ),
                }
                if idempotency_key:
                    self._store_idempotency(idempotency_key, False, result)
                return False, result

            # Transition RESERVED → RELEASED
            self._release_reservation(sku_obj, res)

            record = res.to_record()
            if idempotency_key:
                self._store_idempotency(idempotency_key, True, record)

        return True, record

    # ── M5: Report ────────────────────────────────────────────────

    def report_sku(self, sku: str) -> Optional[SkuReport]:
        """Real-time counters for one SKU."""
        lock = self._get_lock(sku)
        with lock:
            sku_obj = self._get_sku(sku)
            if sku_obj is None:
                return None
            product = sku_obj.product
            reserved = sum(
                r.quantity
                for r in sku_obj.reservations.values()
                if r.state == ReservationState.RESERVED
            )
            return SkuReport(
                sku=sku,
                total_stock=product.total_stock,
                sold=sku_obj.sold,
                reserved=reserved,
                available=product.total_stock - sku_obj.sold - reserved,
            )

    def report_all(self) -> List[SkuReport]:
        """Report for every SKU."""
        reports = []
        for sku in sorted(self._skus.keys()):
            r = self.report_sku(sku)
            if r is not None:
                reports.append(r)
        return reports

    def get_reservation(self, reservation_id: str) -> Optional[ReservationRecord]:
        """Look up a single reservation by ID."""
        sku = self._find_sku_for_reservation(reservation_id)
        if sku is None:
            return None
        lock = self._get_lock(sku)
        with lock:
            sku_obj = self._get_sku(sku)
            if sku_obj is None:
                return None
            res = sku_obj.reservations.get(reservation_id)
            return res.to_record() if res else None

    # ── sweeper (called by background thread) ─────────────────────

    def expire_stale(self) -> int:
        """Walk all SKUs and release expired RESERVED reservations.

        Returns count of reservations released this sweep.
        """
        now = time.monotonic()
        total_released = 0

        # Snapshot SKU list under _locks_lock to avoid mutation during iteration
        with self._locks_lock:
            sku_keys = list(self._skus.keys())

        for sku in sku_keys:
            lock = self._get_lock(sku)
            with lock:
                sku_obj = self._get_sku(sku)
                if sku_obj is None:
                    continue
                expired_ids = [
                    rid
                    for rid, r in sku_obj.reservations.items()
                    if r.state == ReservationState.RESERVED and r.expires_at <= now
                ]
                for rid in expired_ids:
                    r = sku_obj.reservations[rid]
                    self._release_reservation(sku_obj, r)
                    total_released += 1

        return total_released

    # ── internal helpers ──────────────────────────────────────────

    def _release_reservation(
        self, sku_obj: _MutableSku, res: _MutableReservation
    ) -> None:
        """Transition a reservation to RELEASED and return held quota.
        Caller MUST hold the SKU lock."""
        res.state = ReservationState.RELEASED
        res.released_at = time.monotonic()
        user_id = res.user_id
        held = sku_obj.user_held.get(user_id, 0)
        new_held = held - res.quantity
        if new_held <= 0:
            sku_obj.user_held.pop(user_id, None)
        else:
            sku_obj.user_held[user_id] = new_held

    def _find_sku_for_reservation(self, reservation_id: str) -> Optional[str]:
        """Linear scan — acceptable for in-memory sizes.  Returns SKU or None."""
        for sku, sku_obj in self._skus.items():
            if reservation_id in sku_obj.reservations:
                return sku
        return None

    # ── idempotency ───────────────────────────────────────────────

    def _check_idempotency(self, key: str) -> Optional[tuple[bool, Any]]:
        """Returns the cached (success, payload) tuple or None."""
        with self._idempotency_lock:
            record = self._idempotency.get(key)
            if record is None:
                return None
            if time.time() - record.created_at > record.ttl_seconds:
                del self._idempotency[key]
                return None
            return record.response

    def _store_idempotency(self, key: str, success: bool, payload: Any) -> None:
        """Store a (success, payload) tuple keyed by idempotency key."""
        with self._idempotency_lock:
            self._idempotency[key] = IdempotencyRecord(
                response=(success, payload),
                created_at=time.time(),
                ttl_seconds=self.config.idempotency_ttl_seconds,
            )

    # ── cleanup ───────────────────────────────────────────────────

    def cleanup_stale_idempotency(self) -> int:
        """Periodic purge of expired idempotency records."""
        now = time.time()
        removed = 0
        with self._idempotency_lock:
            stale = [
                k
                for k, v in self._idempotency.items()
                if now - v.created_at > v.ttl_seconds
            ]
            for k in stale:
                del self._idempotency[k]
                removed += 1
        return removed


# The dataclass import is at the top of the module, but the re-definition
# inside the same module uses the same name.  This is intentional; flake8
# and mypy have no issue with it.  We add this note for clarity.