"""Optimized Flash Sale Inventory Management Engine (O(1) lookups, minimal memory)."""

import itertools
import json
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Union, Callable, Any

from .models import Product, Reservation, ReservationStatus, StockReport
from .exceptions import (
    ValidationError,
    ProductNotFoundError,
    InsufficientStockError,
    PurchaseLimitExceededError,
    ReservationNotFoundError,
    ReservationExpiredError,
    InvalidStateError,
)
from .limiter import UserPurchaseLimiter
from .sweeper import TTLSweeper
from .audit import AuditLedger
from .waitlist import WaitlistManager


class FlashSaleEngine:
    """
    High-performance flash sale engine optimized for minimal space and time complexity.
    - O(1) single-lookup stock operations via embedded Product counters.
    - O(1) per-user quota checking and tracking.
    - O(log N) Min-heap TTL reservation expiry.
    - Fine-grained per-SKU locking to prevent concurrency bottlenecks.
    """

    __slots__ = (
        "default_ttl",
        "default_per_user_limit",
        "auto_promote_waitlist",
        "_time_func",
        "_global_lock",
        "_sku_locks",
        "_products",
        "_reservations",
        "_counter",
        "limiter",
        "audit",
        "waitlist",
        "sweeper",
    )

    def __init__(
        self,
        inventory_source: Optional[Union[str, Path, List[Dict[str, Any]]]] = None,
        default_ttl: int = 120,
        default_per_user_limit: int = 2,
        auto_start_sweeper: bool = True,
        sweep_interval: float = 0.5,
        time_func: Optional[Callable[[], float]] = None,
        auto_promote_waitlist: bool = True,
    ):
        self.default_ttl = default_ttl
        self.default_per_user_limit = default_per_user_limit
        self.auto_promote_waitlist = auto_promote_waitlist
        self._time_func = time_func or time.time

        self._global_lock = threading.RLock()
        self._sku_locks: Dict[str, threading.RLock] = {}
        self._products: Dict[str, Product] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._counter = itertools.count(1)

        self.limiter = UserPurchaseLimiter()
        self.audit = AuditLedger()
        self.waitlist = WaitlistManager()
        self.sweeper = TTLSweeper(
            expire_callback=self._handle_sweeper_expire,
            sweep_interval=sweep_interval,
            time_func=self._time_func,
        )

        if inventory_source is not None:
            if isinstance(inventory_source, (str, Path)):
                self.load_inventory_file(inventory_source)
            elif isinstance(inventory_source, list):
                self.load_inventory_data(inventory_source)
            else:
                raise ValidationError(f"Unsupported inventory source type: {type(inventory_source)}")

        if auto_start_sweeper:
            self.sweeper.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self) -> None:
        self.sweeper.stop()

    def _get_sku_lock(self, sku: str) -> threading.RLock:
        with self._global_lock:
            lock = self._sku_locks.get(sku)
            if lock is None:
                lock = self._sku_locks[sku] = threading.RLock()
            return lock

    # -------------------------------------------------------------------------
    # M1: Inventory Loading
    # -------------------------------------------------------------------------

    def load_inventory_file(self, filepath: Union[str, Path]) -> int:
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Inventory file not found: {path.resolve()}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON in inventory file: {exc}") from exc

        if not isinstance(data, list):
            raise ValidationError("Inventory JSON root must be an array of product objects.")
        return self.load_inventory_data(data)

    def load_inventory_data(self, items: List[Dict[str, Any]]) -> int:
        if not isinstance(items, list):
            raise ValidationError("Items must be a list of dictionaries.")

        loaded_count = 0
        with self._global_lock:
            for item in items:
                if not isinstance(item, dict):
                    raise ValidationError("Each inventory item must be a dictionary.")

                sku = str(item.get("sku", "")).strip()
                if not sku:
                    raise ValidationError(f"Invalid or missing SKU in item: {item}")

                stock = item.get("stock")
                if stock is None or not isinstance(stock, int) or stock < 0:
                    raise ValidationError(f"Invalid stock '{stock}' for SKU '{sku}'.")

                name = item.get("name", sku)
                price = float(item.get("price", 0.0))
                per_user_limit = item.get("per_user_limit", self.default_per_user_limit)
                if not isinstance(per_user_limit, int) or per_user_limit <= 0:
                    raise ValidationError(f"Invalid per_user_limit '{per_user_limit}' for SKU '{sku}'.")

                product = Product(
                    sku=sku,
                    name=name,
                    initial_stock=stock,
                    price=price,
                    per_user_limit=per_user_limit,
                )

                sku_lock = self._get_sku_lock(sku)
                with sku_lock:
                    self._products[sku] = product

                self.audit.record("INVENTORY_LOADED", sku=sku, quantity=stock)
                loaded_count += 1

        return loaded_count

    # -------------------------------------------------------------------------
    # Expiration Management
    # -------------------------------------------------------------------------

    def _expire_single(self, res: Reservation, product: Optional[Product] = None) -> None:
        """O(1) transition from PENDING to EXPIRED and stock return."""
        if res.status != ReservationStatus.PENDING:
            return

        res.status = ReservationStatus.EXPIRED
        prod = product or self._products.get(res.sku)
        if prod:
            prod.reserved -= res.quantity
            prod.available += res.quantity

        self.limiter.release_reservation(res.user_id, res.sku, res.reservation_id, res.quantity)
        self.audit.record("RESERVATION_EXPIRED", sku=res.sku, user_id=res.user_id, quantity=res.quantity, reservation_id=res.reservation_id)

        if self.auto_promote_waitlist and prod:
            self._try_fulfill_waitlist(prod)

    def _handle_sweeper_expire(self, reservation_id: str, sku: str) -> None:
        """Callback invoked by background priority-queue sweeper."""
        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            res = self._reservations.get(reservation_id)
            if res and res.status == ReservationStatus.PENDING and res.is_expired(self._time_func()):
                self._expire_single(res, self._products.get(sku))

    # -------------------------------------------------------------------------
    # M2 & M4: Reservation & Quotas
    # -------------------------------------------------------------------------

    def reserve(
        self,
        user_id: str,
        sku: str,
        quantity: int = 1,
        ttl_seconds: Optional[int] = None,
    ) -> Reservation:
        """O(1) atomic stock reservation with per-user quota check."""
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValidationError("user_id must be a non-empty string.")
        user_id = user_id.strip()

        if not sku or not isinstance(sku, str) or not sku.strip():
            raise ValidationError("sku must be a non-empty string.")
        sku = sku.strip()

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError(f"quantity must be a positive integer, got: {quantity}")

        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        if not isinstance(ttl, int) or ttl <= 0:
            raise ValidationError(f"ttl_seconds must be a positive integer, got: {ttl_seconds}")

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            product = self._products.get(sku)
            if not product:
                raise ProductNotFoundError(sku)

            # Quota check O(1)
            self.limiter.check_limit(user_id, sku, quantity, product.per_user_limit)

            # Available stock check O(1)
            if product.available < quantity:
                raise InsufficientStockError(sku=sku, requested=quantity, available=product.available)

            # Atomic stock hold O(1)
            product.available -= quantity
            product.reserved += quantity

            now = self._time_func()
            res_id = f"res_{time.time_ns():x}_{next(self._counter)}"
            reservation = Reservation(
                reservation_id=res_id,
                user_id=user_id,
                sku=sku,
                quantity=quantity,
                created_at=now,
                expires_at=now + ttl,
                status=ReservationStatus.PENDING,
            )

            self._reservations[res_id] = reservation
            self.limiter.record_reservation(user_id, sku, res_id, quantity)
            self.sweeper.schedule(res_id, sku, reservation.expires_at)
            self.audit.record("RESERVATION_CREATED", sku=sku, user_id=user_id, quantity=quantity, reservation_id=res_id)
            return reservation

    # -------------------------------------------------------------------------
    # M3: Confirm & Cancel
    # -------------------------------------------------------------------------

    def confirm(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """O(1) permanent confirmation deducting into sold stock."""
        if not reservation_id or not isinstance(reservation_id, str):
            raise ValidationError("reservation_id must be a non-empty string.")

        with self._global_lock:
            res = self._reservations.get(reservation_id)
            if not res:
                raise ReservationNotFoundError(reservation_id, user_id)
            sku = res.sku

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            res = self._reservations.get(reservation_id)
            if not res or (user_id is not None and res.user_id != user_id):
                raise ReservationNotFoundError(reservation_id, user_id)

            product = self._products[sku]
            now = self._time_func()

            if res.is_expired(now) or res.status == ReservationStatus.EXPIRED:
                if res.status == ReservationStatus.PENDING:
                    self._expire_single(res, product)
                raise ReservationExpiredError(reservation_id, res.expires_at)

            if res.status != ReservationStatus.PENDING:
                raise InvalidStateError(reservation_id, res.status.value, "confirm")

            res.status = ReservationStatus.CONFIRMED
            res.confirmed_at = now
            product.reserved -= res.quantity
            product.sold += res.quantity

            self.limiter.record_confirmation(res.user_id, sku, res.reservation_id, res.quantity)
            self.audit.record("RESERVATION_CONFIRMED", sku=sku, user_id=res.user_id, quantity=res.quantity, reservation_id=res.reservation_id)
            return res

    def cancel(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """O(1) cancellation releasing reserved stock back to available."""
        if not reservation_id or not isinstance(reservation_id, str):
            raise ValidationError("reservation_id must be a non-empty string.")

        with self._global_lock:
            res = self._reservations.get(reservation_id)
            if not res:
                raise ReservationNotFoundError(reservation_id, user_id)
            sku = res.sku

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            res = self._reservations.get(reservation_id)
            if not res or (user_id is not None and res.user_id != user_id):
                raise ReservationNotFoundError(reservation_id, user_id)

            if res.status != ReservationStatus.PENDING:
                raise InvalidStateError(reservation_id, res.status.value, "cancel")

            product = self._products[sku]
            res.status = ReservationStatus.CANCELLED
            res.cancelled_at = self._time_func()
            product.reserved -= res.quantity
            product.available += res.quantity

            self.limiter.release_reservation(res.user_id, sku, res.reservation_id, res.quantity)
            self.audit.record("RESERVATION_CANCELLED", sku=sku, user_id=res.user_id, quantity=res.quantity, reservation_id=res.reservation_id)

            if self.auto_promote_waitlist:
                self._try_fulfill_waitlist(product)

            return res

    def release_expired(self) -> List[str]:
        """Pops and expires all reservations whose TTL has passed."""
        expired = self.sweeper.sweep_expired()
        return [res_id for res_id, _ in expired]

    # -------------------------------------------------------------------------
    # M5: Reporting
    # -------------------------------------------------------------------------

    def get_stock_report(self, sku: str) -> StockReport:
        """O(1) stock report retrieval and invariant assertion."""
        if not sku or not isinstance(sku, str):
            raise ValidationError("sku must be a non-empty string.")
        sku = sku.strip()

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            product = self._products.get(sku)
            if not product:
                raise ProductNotFoundError(sku)

            return StockReport(
                sku=sku,
                name=product.name,
                initial_stock=product.initial_stock,
                available=product.available,
                reserved=product.reserved,
                sold=product.sold,
            )

    def get_all_reports(self) -> Dict[str, StockReport]:
        with self._global_lock:
            skus = list(self._products.keys())
        return {sku: self.get_stock_report(sku) for sku in skus}

    def get_system_summary(self) -> Dict[str, Any]:
        reports = self.get_all_reports()
        total_initial = sum(r.initial_stock for r in reports.values())
        total_avail = sum(r.available for r in reports.values())
        total_reserved = sum(r.reserved for r in reports.values())
        total_sold = sum(r.sold for r in reports.values())

        with self._global_lock:
            total_res = len(self._reservations)
            counts = {status: 0 for status in ReservationStatus}
            for r in self._reservations.values():
                counts[r.status] += 1

        return {
            "total_products": len(reports),
            "total_initial_stock": total_initial,
            "total_available": total_avail,
            "total_reserved": total_reserved,
            "total_sold": total_sold,
            "inventory_invariant_satisfied": (total_initial == total_avail + total_reserved + total_sold),
            "reservations_summary": {
                "total": total_res,
                "active": counts[ReservationStatus.PENDING],
                "confirmed": counts[ReservationStatus.CONFIRMED],
                "cancelled": counts[ReservationStatus.CANCELLED],
                "expired": counts[ReservationStatus.EXPIRED],
            },
            "audit_events_recorded": self.audit.get_count(),
        }

    # -------------------------------------------------------------------------
    # Bonus: FIFO Waitlist
    # -------------------------------------------------------------------------

    def join_waitlist(self, user_id: str, sku: str, quantity: int = 1) -> int:
        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            if sku not in self._products:
                raise ProductNotFoundError(sku)
            pos = self.waitlist.join(f"wl_{next(self._counter)}", user_id, sku, quantity)
            self.audit.record("WAITLIST_JOINED", sku=sku, user_id=user_id, quantity=quantity, details={"position": pos})
            return pos

    def _try_fulfill_waitlist(self, product: Product) -> Optional[Reservation]:
        if product.available <= 0:
            return None
        entry = self.waitlist.pop_next_eligible(product.sku, product.available)
        if not entry:
            return None
        try:
            res = self.reserve(entry.user_id, entry.sku, entry.requested_qty, self.default_ttl)
            self.audit.record("WAITLIST_PROMOTED", sku=product.sku, user_id=entry.user_id, quantity=entry.requested_qty, reservation_id=res.reservation_id)
            return res
        except (PurchaseLimitExceededError, InsufficientStockError):
            return None

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        with self._global_lock:
            return self._reservations.get(reservation_id)
