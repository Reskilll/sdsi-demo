"""Core reservation engine — thread-safe, lock-guarded inventory management."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from errors import (
    InsufficientStockError,
    InvalidDataError,
    InvalidTransitionError,
    PerUserLimitError,
    ReservationExpiredError,
    ReservationNotFoundError,
)
from models import (
    Product,
    ProductState,
    ReservationRecord,
    ReservationState,
    UserSkuState,
    new_id,
)


class InventoryReservationEngine:
    """Thread-safe reservation engine with background expiry sweeper.

    All mutable state is guarded by a single :class:`threading.RLock`.
    """

    def __init__(self, products: Dict[str, Product]) -> None:
        self._products: Dict[str, Product] = dict(products)
        self._product_states: Dict[str, ProductState] = {
            sku: ProductState(total=p.total) for sku, p in self._products.items()
        }
        # reservation_id → ReservationRecord
        self._reservations: Dict[str, ReservationRecord] = {}
        # Lock order to keep: (user_id, sku) → UserSkuState
        self._user_states: Dict[Tuple[str, str], UserSkuState] = {}

        self._lock = threading.RLock()
        self._sweeper_active = threading.Event()
        self._sweeper_thread: Optional[threading.Thread] = None
        self._on_expiry_hook: Optional[Callable[[str], None]] = None
        self._order_counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reserve(self, sku: str, user_id: str, qty: int) -> Tuple[str, datetime]:
        """Atomically reserve *qty* units of *sku* for *user_id*.

        Returns (reservation_id, expires_at).
        Raises InvalidDataError, InsufficientStockError, or PerUserLimitError.
        """
        self._validate_qty(qty)
        if not user_id or not isinstance(user_id, str):
            raise InvalidDataError("user_id must be a non-empty string")

        product = self._products.get(sku)
        if product is None:
            raise InvalidDataError(f"Unknown SKU: {sku!r}")

        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(
            now.timestamp() + product.ttl_seconds, tz=timezone.utc
        )

        rid = new_id()

        with self._lock:
            state = self._product_states[sku]
            if qty > state.available:
                raise InsufficientStockError(
                    f"Requested {qty} units of '{sku}', "
                    f"only {state.available} available"
                )

            user_key = (user_id, sku)
            us = self._user_states.setdefault(user_key, UserSkuState())
            # Reconcile user state against current reservations
            self._reconcile_user_state(user_key, us)

            if us.total_held + qty > product.per_user_limit:
                raise PerUserLimitError(
                    f"User '{user_id}' may hold at most {product.per_user_limit} units "
                    f"of '{sku}' (currently holds {us.total_held})"
                )

            # Everything checks out — create reservation
            record = ReservationRecord(
                reservation_id=rid,
                sku=sku,
                user_id=user_id,
                qty=qty,
                state=ReservationState.active,
                created_at=now,
                expires_at=expires_at,
            )
            self._reservations[rid] = record
            state.reserved += qty
            us.reserved += qty

        return rid, expires_at

    def confirm(self, reservation_id: str) -> None:
        """Permanently deduct reserved stock (moves reserved → sold)."""
        with self._lock:
            record = self._get_active_reservation(reservation_id)
            state = self._product_states[record.sku]
            user_key = (record.user_id, record.sku)
            us = self._user_states.setdefault(user_key, UserSkuState())

            record.state = ReservationState.confirmed
            state.reserved -= record.qty
            state.sold += record.qty
            us.reserved -= record.qty
            us.sold += record.qty

    def cancel(self, reservation_id: str) -> None:
        """Release reserved stock (reserved → available)."""
        with self._lock:
            record = self._reservations.get(reservation_id)
            if record is None:
                raise ReservationNotFoundError(
                    f"Reservation '{reservation_id}' not found"
                )

            if record.state not in (ReservationState.active, ReservationState.expired):
                raise InvalidTransitionError(
                    f"Cannot cancel reservation '{reservation_id}' "
                    f"in state '{record.state.value}'"
                )

            state = self._product_states[record.sku]
            user_key = (record.user_id, record.sku)
            us = self._user_states.get(user_key)

            if record.state == ReservationState.active:
                state.reserved -= record.qty
                if us:
                    us.reserved -= record.qty
            # If expired, the stock was already freed by the sweeper/lazy check

            record.state = ReservationState.cancelled

    def report(self, sku: Optional[str] = None) -> Dict:
        """Return stock snapshot for one SKU or all.

        Always runs under lock and performs lazy expiry before reading.
        """
        with self._lock:
            self._lazy_expiry()
            if sku is not None:
                return self._report_one(sku)
            return {s: self._report_one(s) for s in self._product_states}

    # ------------------------------------------------------------------
    # Background sweeper
    # ------------------------------------------------------------------

    def start_sweeper(
        self,
        interval: float = 5.0,
        on_expiry: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Start a background thread that releases expired reservations.

        *interval* — seconds between sweeps (default 5).
        *on_expiry* — optional callback(reservation_id) invoked with lock held.
        """
        if self._sweeper_active.is_set():
            return  # already running
        self._sweeper_active.set()
        self._on_expiry_hook = on_expiry

        def _sweep() -> None:
            while self._sweeper_active.is_set():
                self._release_expired()
                time.sleep(interval)

        self._sweeper_thread = threading.Thread(target=_sweep, daemon=True)
        self._sweeper_thread.start()

    def stop_sweeper(self, timeout: float = 2.0) -> None:
        """Signal the sweeper thread to stop and join it."""
        self._sweeper_active.clear()
        if self._sweeper_thread and self._sweeper_thread.is_alive():
            self._sweeper_thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _release_expired(self) -> int:
        """Release all expired reservations. Returns count released."""
        now = datetime.now(timezone.utc)
        released = 0
        with self._lock:
            expired_ids = [
                rid
                for rid, rec in self._reservations.items()
                if rec.state == ReservationState.active and now >= rec.expires_at
            ]
            for rid in expired_ids:
                rec = self._reservations[rid]
                rec.state = ReservationState.expired
                state = self._product_states[rec.sku]
                state.reserved -= rec.qty
                user_key = (rec.user_id, rec.sku)
                us = self._user_states.get(user_key)
                if us:
                    us.reserved -= rec.qty
                if self._on_expiry_hook:
                    self._on_expiry_hook(rid)
                released += 1
        return released

    def _lazy_expiry(self) -> None:
        """Inline expiry check — run on read/confirm/report (caller holds lock)."""
        now = datetime.now(timezone.utc)
        for rec in list(self._reservations.values()):
            if rec.state == ReservationState.active and now >= rec.expires_at:
                rec.state = ReservationState.expired
                state = self._product_states[rec.sku]
                state.reserved -= rec.qty
                user_key = (rec.user_id, rec.sku)
                us = self._user_states.get(user_key)
                if us:
                    us.reserved -= rec.qty

    def _get_active_reservation(self, reservation_id: str) -> ReservationRecord:
        """Retrieve and validate an active (non-expired, non-confirmed) reservation.

        Caller *must* hold the lock.
        """
        record = self._reservations.get(reservation_id)
        if record is None:
            raise ReservationNotFoundError(
                f"Reservation '{reservation_id}' not found"
            )

        # Lazy-expiry check
        if record.state == ReservationState.active and record.has_expired():
            record.state = ReservationState.expired
            state = self._product_states[record.sku]
            state.reserved -= record.qty
            user_key = (record.user_id, record.sku)
            us = self._user_states.get(user_key)
            if us:
                us.reserved -= record.qty

        if record.state == ReservationState.expired:
            raise ReservationExpiredError(
                f"Reservation '{reservation_id}' has expired"
            )
        if record.state == ReservationState.confirmed:
            raise InvalidTransitionError(
                f"Reservation '{reservation_id}' is already confirmed"
            )
        if record.state == ReservationState.cancelled:
            raise InvalidTransitionError(
                f"Reservation '{reservation_id}' has been cancelled"
            )
        return record

    def _reconcile_user_state(self, user_key: Tuple[str, str], us: UserSkuState) -> None:
        """Scan the user's reservations and rebuild counters to avoid drift.

        Caller holds the lock.  This keeps user stats consistent if, e.g.,
        an internal inconsistency crept in during recovery.
        """
        # Simple guard: recalculate from live reservations for this user+sku
        reserved = 0
        sold = 0
        for rec in self._reservations.values():
            if rec.user_id == user_key[0] and rec.sku == user_key[1]:
                if rec.state == ReservationState.active:
                    reserved += rec.qty
                elif rec.state == ReservationState.confirmed:
                    sold += rec.qty
        us.reserved = reserved
        us.sold = sold

    @staticmethod
    def _validate_qty(qty: int) -> None:
        if not isinstance(qty, int) or qty <= 0:
            raise InvalidDataError(
                f"Quantity must be a positive integer, got {qty!r}"
            )

    def _report_one(self, sku: str) -> Dict:
        """Return snapshot for a single SKU (caller holds lock)."""
        state = self._product_states.get(sku)
        if state is None:
            raise InvalidDataError(f"Unknown SKU: {sku!r}")
        return {
            "sku": sku,
            "total": state.total,
            "available": state.available,
            "reserved": state.reserved,
            "sold": state.sold,
        }