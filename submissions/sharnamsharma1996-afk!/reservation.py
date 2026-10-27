"""Flash-sale inventory reservation system — core library.

Thread-safe, TTL-based reservation with lazy expiry, per-SKU user limits,
and JSON file persistence.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Product:
    sku: str
    name: str
    total_stock: int
    per_user_limit: int  # 0 = no limit


@dataclass
class Reservation:
    id: str
    user_id: str
    sku: str
    quantity: int
    expires_at: float
    status: str  # "active" | "confirmed" | "cancelled" | "expired"


@dataclass
class SkuReport:
    sku: str
    name: str
    total_stock: int
    available: int
    reserved: int
    sold: int


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class InventoryError(Exception):
    """Base exception for inventory operations."""


class SkuNotFound(InventoryError):
    """The requested SKU does not exist."""


class InsufficientStock(InventoryError):
    """Not enough available stock to fulfil the request."""


class ReservationNotFound(InventoryError):
    """The reservation ID does not exist."""


class ReservationExpired(InventoryError):
    """The reservation has expired and can no longer be used."""


class ReservationNotActive(InventoryError):
    """The reservation is not in 'active' status (already confirmed/cancelled)."""


class UserLimitExceeded(InventoryError):
    """The user has reached their per-SKU purchase limit."""


class InvalidQuantity(InventoryError):
    """The requested quantity must be a positive integer."""


class Unauthorized(InventoryError):
    """The user is not authorized for this operation (e.g. confirming another user's reservation)."""


class DataLoadError(InventoryError):
    """Failed to load or parse the inventory data file."""


# ---------------------------------------------------------------------------
# Core system
# ---------------------------------------------------------------------------

class InventorySystem:
    """Thread-safe flash-sale inventory reservation engine.

    Uses lazy TTL eviction: expired reservations are cleaned up on every
    read or write operation, so no background thread is needed.

    Parameters
    ----------
    state_file:
        Optional path to a JSON file for persistence.  When set, every
        mutation (and product load) is auto-saved.  Pass ``None`` for an
        ephemeral, in-memory instance (useful in tests).
    ttl:
        Default reservation time-to-live in seconds.  Can be overridden
        per-reservation via the ``reserve()`` method.  Also overridden
        when ``load_products`` reads a ``config.reservation_ttl_seconds``
        from inventory JSON.
    """

    def __init__(self, state_file: Optional[str] = None, ttl: float = 120.0):
        self._lock = threading.Lock()
        self._state_file = Path(state_file) if state_file else None
        self._ttl = float(ttl)

        # Primary state (all guarded by _lock)
        self._products: dict[str, Product] = {}
        self._reservations: dict[str, Reservation] = {}
        # _sold tracks *confirmed* sold quantities per SKU
        self._sold: dict[str, int] = {}
        # Per-user confirmed counts:  user_id -> {sku: count}
        self._user_confirmed: dict[str, dict[str, int]] = {}

        if self._state_file and self._state_file.exists():
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_products(self, path: str | Path) -> None:
        """Load product definitions and optional config from a JSON file.

        The file must contain a ``"products"`` array.  Each product
        requires ``sku`` and ``total_stock``; ``name`` and
        ``per_user_limit`` are optional.

        An optional ``"config"`` object may supply
        ``reservation_ttl_seconds`` to override the system default.
        """
        raw = _read_json(path)

        products: list[dict[str, Any]]
        if isinstance(raw, list):
            products = raw
        elif isinstance(raw, dict):
            products = raw.get("products", [])
        else:
            raise DataLoadError(f"Expected a JSON object or array, got {type(raw).__name__}")

        if not isinstance(products, list):
            raise DataLoadError(f"'products' must be a list, got {type(products).__name__}")

        with self._lock:
            self._products.clear()
            self._sold.clear()
            self._reservations.clear()
            self._user_confirmed.clear()

            for entry in products:
                if not isinstance(entry, dict):
                    raise DataLoadError(f"Each product must be a JSON object, got {type(entry).__name__}")
                sku = _require_str(entry, "sku")
                total_stock = _require_int(entry, "total_stock")
                if total_stock < 0:
                    raise DataLoadError(f"total_stock for '{sku}' must be >= 0, got {total_stock}")
                name = entry.get("name", sku)
                per_user_limit = int(entry.get("per_user_limit", 0) or 0)
                if per_user_limit < 0:
                    raise DataLoadError(f"per_user_limit for '{sku}' must be >= 0, got {per_user_limit}")

                if sku in self._products:
                    raise DataLoadError(f"Duplicate SKU: '{sku}'")
                self._products[sku] = Product(
                    sku=sku,
                    name=str(name),
                    total_stock=total_stock,
                    per_user_limit=per_user_limit,
                )
                self._sold[sku] = 0

            # Optional config
            if isinstance(raw, dict):
                config = raw.get("config")
                if isinstance(config, dict) and "reservation_ttl_seconds" in config:
                    ttl = _require_float(config, "reservation_ttl_seconds")
                    if ttl <= 0:
                        raise DataLoadError("reservation_ttl_seconds must be > 0")
                    self._ttl = ttl

        self._save()

    def reserve(
        self,
        user_id: str,
        sku: str,
        quantity: int = 1,
        ttl: Optional[float] = None,
    ) -> Reservation:
        """Reserve ``quantity`` units of ``sku`` for ``user_id``.

        Returns the new ``Reservation``.  Raises ``InvalidQuantity``,
        ``SkuNotFound``, ``InsufficientStock``, or ``UserLimitExceeded``.
        """
        _require_nonempty(user_id, "user_id")
        _require_positive(quantity, "quantity")
        ttl = float(ttl) if ttl is not None else self._ttl
        if ttl <= 0:
            raise ValueError("ttl must be > 0")

        with self._lock:
            self._sweep()

            product = self._products.get(sku)
            if product is None:
                raise SkuNotFound(f"SKU not found: '{sku}'")

            # Check stock
            active_reserved = self._active_reserved(sku)
            sold = self._sold.get(sku, 0)
            available = product.total_stock - active_reserved - sold
            if quantity > available:
                raise InsufficientStock(
                    f"Requested {quantity} of '{sku}' but only {available} available "
                    f"(total={product.total_stock}, sold={sold}, reserved={active_reserved})"
                )

            # Check per-user limit (aggregate: confirmed + active reservs)
            if product.per_user_limit > 0:
                user_confirmed = self._user_confirmed.get(user_id, {}).get(sku, 0)
                user_active = self._user_active_count(user_id, sku)
                already_claimed = user_confirmed + user_active
                if already_claimed + quantity > product.per_user_limit:
                    raise UserLimitExceeded(
                        f"User '{user_id}' already has {already_claimed} of '{sku}' "
                        f"(confirmed={user_confirmed}, reserved={user_active}); "
                        f"per-user limit is {product.per_user_limit}"
                    )

            resv_id = _make_reservation_id()
            reservation = Reservation(
                id=resv_id,
                user_id=user_id,
                sku=sku,
                quantity=quantity,
                expires_at=time.time() + ttl,
                status="active",
            )
            self._reservations[resv_id] = reservation

        self._save()
        return reservation

    def confirm(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """Permanently deduct the stock for an active reservation.

        If ``user_id`` is provided the reservation is checked to belong
        to that user (prevents cross-user confirmation).

        Returns the updated ``Reservation`` with ``status == "confirmed"``.
        """
        _require_nonempty(reservation_id, "reservation_id")

        with self._lock:
            self._sweep()

            resv = self._reservations.get(reservation_id)
            if resv is None:
                raise ReservationNotFound(f"Reservation not found: '{reservation_id}'")

            if resv.status == "expired":
                raise ReservationExpired("Reservation has expired")
            if resv.status == "confirmed":
                raise ReservationNotActive("Reservation is already confirmed")
            if resv.status == "cancelled":
                raise ReservationNotActive("Reservation has been cancelled")

            if user_id is not None and user_id != resv.user_id:
                raise Unauthorized(
                    f"Reservation '{reservation_id}' belongs to user '{resv.user_id}', not '{user_id}'"
                )

            resv.status = "confirmed"
            self._sold[resv.sku] = self._sold.get(resv.sku, 0) + resv.quantity

            # Track user confirmed counts
            uc = self._user_confirmed.setdefault(resv.user_id, {})
            uc[resv.sku] = uc.get(resv.sku, 0) + resv.quantity

        self._save()
        return resv

    def cancel(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """Release an active reservation, returning stock to the pool.

        If ``user_id`` is provided the reservation is checked to belong
        to that user.
        """
        _require_nonempty(reservation_id, "reservation_id")

        with self._lock:
            self._sweep()

            resv = self._reservations.get(reservation_id)
            if resv is None:
                raise ReservationNotFound(f"Reservation not found: '{reservation_id}'")

            if resv.status in ("expired", "confirmed"):
                raise ReservationNotActive(
                    f"Cannot cancel reservation with status '{resv.status}'"
                )
            if resv.status == "cancelled":
                raise ReservationNotActive("Reservation is already cancelled")

            if user_id is not None and user_id != resv.user_id:
                raise Unauthorized(
                    f"Reservation '{reservation_id}' belongs to user '{resv.user_id}', not '{user_id}'"
                )

            resv.status = "cancelled"

        self._save()
        return resv

    def report(self, sku: Optional[str] = None) -> list[SkuReport]:
        """Return available/reserved/sold counts.

        If ``sku`` is ``None``, reports all SKUs.  Always sweeps expired
        reservations first so counts are accurate.
        """
        with self._lock:
            self._sweep()
            skus = [sku] if sku else sorted(self._products.keys())

            reports: list[SkuReport] = []
            for s in skus:
                product = self._products.get(s)
                if product is None:
                    raise SkuNotFound(f"SKU not found: '{s}'")
                active = self._active_reserved(s)
                sold = self._sold.get(s, 0)
                available = product.total_stock - active - sold
                reports.append(SkuReport(
                    sku=product.sku,
                    name=product.name,
                    total_stock=product.total_stock,
                    available=max(available, 0),
                    reserved=active,
                    sold=sold,
                ))
            return reports

    def list_reservations(self, user_id: Optional[str] = None) -> list[Reservation]:
        """Return all reservations, optionally filtered by user.

        Expired reservations are swept *before* listing, so active
        reservations are guaranteed to still be valid.
        """
        with self._lock:
            self._sweep()
            result = list(self._reservations.values())
            if user_id:
                result = [r for r in result if r.user_id == user_id]
            return sorted(result, key=lambda r: r.expires_at, reverse=True)

    # ------------------------------------------------------------------
    # Internal helpers (callers must hold _lock)
    # ------------------------------------------------------------------

    def _active_reserved(self, sku: str) -> int:
        """Sum of active-reservation quantities for a SKU."""
        return sum(
            r.quantity
            for r in self._reservations.values()
            if r.sku == sku and r.status == "active"
        )

    def _user_active_count(self, user_id: str, sku: str) -> int:
        """Sum of active-reservation quantities for a user+SKU pair."""
        return sum(
            r.quantity
            for r in self._reservations.values()
            if r.user_id == user_id and r.sku == sku and r.status == "active"
        )

    def _sweep(self) -> None:
        """Mark all expired reservations as 'expired'.

        Must be called with ``_lock`` held.
        """
        now = time.time()
        expired_ids = [
            rid
            for rid, r in self._reservations.items()
            if r.status == "active" and r.expires_at <= now
        ]
        for rid in expired_ids:
            self._reservations[rid].status = "expired"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if self._state_file is None:
            return
        with self._lock:
            data = {
                "products": {
                    sku: {
                        "sku": p.sku,
                        "name": p.name,
                        "total_stock": p.total_stock,
                        "per_user_limit": p.per_user_limit,
                    }
                    for sku, p in self._products.items()
                },
                "reservations": {
                    rid: {
                        "id": r.id,
                        "user_id": r.user_id,
                        "sku": r.sku,
                        "quantity": r.quantity,
                        "expires_at": r.expires_at,
                        "status": r.status,
                    }
                    for rid, r in self._reservations.items()
                },
                "sold": dict(self._sold),
                "user_confirmed": {
                    uid: dict(per_sku)
                    for uid, per_sku in self._user_confirmed.items()
                },
                "ttl": self._ttl,
            }
        # Write outside lock to avoid holding it during I/O
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        tmp.replace(self._state_file)

    def _load(self) -> None:
        """Restore state from the JSON file.

        Called from __init__ before any lock is held, so sweeping is
        deferred — the first public call will sweep expired reservations.
        """
        data = _read_json(self._state_file)
        if not isinstance(data, dict):
            return

        self._ttl = float(data.get("ttl", self._ttl))

        # Restore product catalog
        self._products = {}
        for sku, entry in data.get("products", {}).items():
            self._products[sku] = Product(
                sku=_require_str(entry, "sku"),
                name=entry.get("name", sku),
                total_stock=_require_int(entry, "total_stock"),
                per_user_limit=int(entry.get("per_user_limit", 0) or 0),
            )

        self._sold = {}
        for sku, count in data.get("sold", {}).items():
            self._sold[sku] = int(count)

        self._user_confirmed = {}
        for uid, per_sku in data.get("user_confirmed", {}).items():
            self._user_confirmed[uid] = {sku: int(n) for sku, n in per_sku.items()}

        self._reservations = {}
        for rid, entry in data.get("reservations", {}).items():
            self._reservations[rid] = Reservation(
                id=_require_str(entry, "id"),
                user_id=_require_str(entry, "user_id"),
                sku=_require_str(entry, "sku"),
                quantity=_require_int(entry, "quantity"),
                expires_at=float(entry.get("expires_at", 0)),
                status=_require_str(entry, "status"),
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_reservation_id() -> str:
    return "rsv_" + secrets.token_hex(10)


def _read_json(path: str | Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise DataLoadError(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Invalid JSON in {path}: {exc}")


def _require_str(obj: dict[str, Any], key: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val.strip():
        raise DataLoadError(f"'{key}' must be a non-empty string, got {val!r}")
    return val.strip()


def _require_int(obj: dict[str, Any], key: str) -> int:
    val = obj.get(key)
    try:
        return int(val)
    except (TypeError, ValueError):
        raise DataLoadError(f"'{key}' must be an integer, got {val!r}")


def _require_float(obj: dict[str, Any], key: str) -> float:
    val = obj.get(key)
    try:
        return float(val)
    except (TypeError, ValueError):
        raise DataLoadError(f"'{key}' must be a number, got {val!r}")


def _require_nonempty(val: str, name: str) -> None:
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{name}' must be a non-empty string")


def _require_positive(val: int, name: str) -> None:
    if not isinstance(val, int) or val < 1:
        raise InvalidQuantity(f"'{name}' must be a positive integer, got {val!r}")