"""Core Flash Sale Inventory Management Engine."""

import json
from pathlib import Path
import threading
import time
import uuid
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
    High-performance, thread-safe flash sale inventory engine.
    
    Prevents overselling under extreme concurrency through fine-grained
    per-SKU synchronization, enforces per-user purchase limits, manages
    TTL-based stock reservations, and tracks full auditability.
    """

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

        # Concurrency primitives:
        # Fine-grained per-SKU locks to maximize concurrent throughput across products
        self._global_lock = threading.RLock()
        self._sku_locks: Dict[str, threading.RLock] = {}

        # Core state
        self._products: Dict[str, Product] = {}
        # Stock counters per SKU: sku -> count
        self._available_stock: Dict[str, int] = {}
        self._reserved_stock: Dict[str, int] = {}
        self._sold_stock: Dict[str, int] = {}

        # Reservations lookup: reservation_id -> Reservation
        self._reservations: Dict[str, Reservation] = {}
        # SKU to reservation IDs index: sku -> set(reservation_id)
        self._sku_reservations: Dict[str, set] = {}

        # Subsystems
        self.limiter = UserPurchaseLimiter()
        self.audit = AuditLedger()
        self.waitlist = WaitlistManager()
        self.sweeper = TTLSweeper(
            expire_callback=self._handle_sweeper_expire,
            sweep_interval=sweep_interval,
            time_func=self._time_func,
        )

        # Load inventory if provided
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
        """Stops background sweeper cleanly."""
        self.sweeper.stop()

    def _get_sku_lock(self, sku: str) -> threading.RLock:
        """Retrieves or creates a reentrant lock dedicated to the specific SKU."""
        with self._global_lock:
            if sku not in self._sku_locks:
                self._sku_locks[sku] = threading.RLock()
            return self._sku_locks[sku]

    # -------------------------------------------------------------------------
    # M1: Inventory Loading
    # -------------------------------------------------------------------------

    def load_inventory_file(self, filepath: Union[str, Path]) -> int:
        """
        Loads product catalog and stock levels from a JSON file.
        Returns count of loaded products.
        """
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
        """
        Loads product items from in-memory dictionary list.
        """
        if not isinstance(items, list):
            raise ValidationError("Items must be a list of dictionaries.")

        loaded_count = 0
        with self._global_lock:
            for item in items:
                if not isinstance(item, dict):
                    raise ValidationError("Each inventory item must be a dictionary.")

                sku = item.get("sku")
                if not sku or not isinstance(sku, str) or not sku.strip():
                    raise ValidationError(f"Invalid or missing SKU in item: {item}")
                sku = sku.strip()

                name = item.get("name", sku)
                stock = item.get("stock")
                if stock is None or not isinstance(stock, int) or stock < 0:
                    raise ValidationError(f"Invalid stock '{stock}' for SKU '{sku}'. Must be a non-negative integer.")

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
                    self._available_stock[sku] = stock
                    self._reserved_stock[sku] = 0
                    self._sold_stock[sku] = 0
                    if sku not in self._sku_reservations:
                        self._sku_reservations[sku] = set()

                self.audit.record(
                    event_type="INVENTORY_LOADED",
                    sku=sku,
                    quantity=stock,
                    details={"name": name, "price": price, "per_user_limit": per_user_limit},
                )
                loaded_count += 1

        return loaded_count

    # -------------------------------------------------------------------------
    # Passive Expiration Helper
    # -------------------------------------------------------------------------

    def _passive_expire_sku_reservations(self, sku: str) -> None:
        """
        Checks and expires any reservations for this SKU whose TTL has passed.
        Must be called while holding the sku lock.
        """
        now = self._time_func()
        res_ids = list(self._sku_reservations.get(sku, []))
        for res_id in res_ids:
            res = self._reservations.get(res_id)
            if res and res.status == ReservationStatus.PENDING and res.is_expired(now):
                self._expire_single_reservation(res)

    def _expire_single_reservation(self, res: Reservation) -> None:
        """
        Executes expiration transition for a single reservation.
        Must be called while holding the SKU lock.
        """
        if res.status != ReservationStatus.PENDING:
            return

        res.status = ReservationStatus.EXPIRED
        self._reserved_stock[res.sku] -= res.quantity
        self._available_stock[res.sku] += res.quantity

        # Release user limit quota
        self.limiter.release_reservation(res.user_id, res.sku, res.reservation_id)

        self.audit.record(
            event_type="RESERVATION_EXPIRED",
            sku=res.sku,
            user_id=res.user_id,
            quantity=res.quantity,
            reservation_id=res.reservation_id,
            details={"expired_at": res.expires_at},
        )

        # Trigger waitlist promotion if enabled
        if self.auto_promote_waitlist:
            self._try_fulfill_waitlist(res.sku)

    def _handle_sweeper_expire(self, reservation_id: str, sku: str) -> None:
        """Callback invoked by the background TTL sweeper thread."""
        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            res = self._reservations.get(reservation_id)
            if res and res.status == ReservationStatus.PENDING and res.is_expired(self._time_func()):
                self._expire_single_reservation(res)

    # -------------------------------------------------------------------------
    # M2 & M4: Stock Reservation & Purchase Limit Enforcement
    # -------------------------------------------------------------------------

    def reserve(
        self,
        user_id: str,
        sku: str,
        quantity: int = 1,
        ttl_seconds: Optional[int] = None,
    ) -> Reservation:
        """
        Reserves quantity of SKU stock for user_id for a TTL (default 120s).
        Enforces per-user purchase limits and ensures zero overselling.
        """
        # Input validation
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
            if sku not in self._products:
                raise ProductNotFoundError(sku)

            product = self._products[sku]

            # 1. Passive clean-up of expired reservations for this SKU to free up stock
            self._passive_expire_sku_reservations(sku)

            # 2. Enforce per-user purchase limit (M4)
            limit = product.per_user_limit
            self.limiter.check_limit(user_id, sku, quantity, limit)

            # 3. Check available stock (M2)
            available = self._available_stock[sku]
            if available < quantity:
                raise InsufficientStockError(sku=sku, requested=quantity, available=available)

            # 4. Atomic stock allocation
            self._available_stock[sku] -= quantity
            self._reserved_stock[sku] += quantity

            # 5. Create reservation record
            now = self._time_func()
            res_id = f"res_{uuid.uuid4().hex[:12]}"
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
            self._sku_reservations[sku].add(res_id)

            # 6. Register with limiter and sweeper
            self.limiter.record_reservation(user_id, sku, res_id, quantity)
            self.sweeper.schedule(res_id, sku, reservation.expires_at)

            # 7. Audit log
            self.audit.record(
                event_type="RESERVATION_CREATED",
                sku=sku,
                user_id=user_id,
                quantity=quantity,
                reservation_id=res_id,
                details={"ttl_seconds": ttl, "expires_at": reservation.expires_at},
            )

            return reservation

    # -------------------------------------------------------------------------
    # M3: Confirmation & Cancellation
    # -------------------------------------------------------------------------

    def confirm(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """
        Permanently confirms a reservation and deducts stock into 'sold'.
        Rejects and releases reservation if it has expired.
        """
        if not reservation_id or not isinstance(reservation_id, str):
            raise ValidationError("reservation_id must be a non-empty string.")

        with self._global_lock:
            res = self._reservations.get(reservation_id)
            if not res:
                raise ReservationNotFoundError(reservation_id, user_id)
            sku = res.sku

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            # Re-fetch under lock
            res = self._reservations.get(reservation_id)
            if not res:
                raise ReservationNotFoundError(reservation_id, user_id)

            if user_id is not None and res.user_id != user_id:
                raise ReservationNotFoundError(reservation_id, user_id)

            now = self._time_func()

            # Check if reservation has expired
            if res.is_expired(now) or res.status == ReservationStatus.EXPIRED:
                if res.status == ReservationStatus.PENDING:
                    self._expire_single_reservation(res)
                raise ReservationExpiredError(reservation_id, res.expires_at)

            # Validate state
            if res.status != ReservationStatus.PENDING:
                raise InvalidStateError(reservation_id, res.status.value, "confirm")

            # State transition PENDING -> CONFIRMED
            res.status = ReservationStatus.CONFIRMED
            res.confirmed_at = now

            self._reserved_stock[sku] -= res.quantity
            self._sold_stock[sku] += res.quantity

            # Update limiter from active reservation to confirmed purchase
            self.limiter.record_confirmation(res.user_id, sku, res.reservation_id, res.quantity)

            # Audit log
            self.audit.record(
                event_type="RESERVATION_CONFIRMED",
                sku=sku,
                user_id=res.user_id,
                quantity=res.quantity,
                reservation_id=res.reservation_id,
                details={"confirmed_at": now},
            )

            return res

    def cancel(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        """
        Cancels an active reservation and immediately returns stock to available.
        """
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
            if not res:
                raise ReservationNotFoundError(reservation_id, user_id)

            if user_id is not None and res.user_id != user_id:
                raise ReservationNotFoundError(reservation_id, user_id)

            if res.status != ReservationStatus.PENDING:
                raise InvalidStateError(reservation_id, res.status.value, "cancel")

            now = self._time_func()
            res.status = ReservationStatus.CANCELLED
            res.cancelled_at = now

            self._reserved_stock[sku] -= res.quantity
            self._available_stock[sku] += res.quantity

            # Release quota in limiter
            self.limiter.release_reservation(res.user_id, sku, res.reservation_id)

            # Audit log
            self.audit.record(
                event_type="RESERVATION_CANCELLED",
                sku=sku,
                user_id=res.user_id,
                quantity=res.quantity,
                reservation_id=res.reservation_id,
                details={"cancelled_at": now},
            )

            # Check waitlist for reclaimed stock
            if self.auto_promote_waitlist:
                self._try_fulfill_waitlist(sku)

            return res

    def release_expired(self) -> List[str]:
        """
        Manually triggers a sweep of expired reservations across all products.
        Returns list of expired reservation IDs.
        """
        expired = self.sweeper.sweep_expired()
        return [res_id for res_id, _ in expired]

    # -------------------------------------------------------------------------
    # M5: Reporting
    # -------------------------------------------------------------------------

    def get_stock_report(self, sku: str) -> StockReport:
        """
        Returns stock counts (initial, available, reserved, sold) for a given SKU.
        Validates the strict consistency invariant: initial == available + reserved + sold.
        """
        if not sku or not isinstance(sku, str):
            raise ValidationError("sku must be a non-empty string.")
        sku = sku.strip()

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            if sku not in self._products:
                raise ProductNotFoundError(sku)

            # Passive expiry before report
            self._passive_expire_sku_reservations(sku)

            product = self._products[sku]
            avail = self._available_stock[sku]
            res = self._reserved_stock[sku]
            sold = self._sold_stock[sku]

            return StockReport(
                sku=sku,
                name=product.name,
                initial_stock=product.initial_stock,
                available=avail,
                reserved=res,
                sold=sold,
            )

    def get_all_reports(self) -> Dict[str, StockReport]:
        """Returns stock reports for all loaded products."""
        with self._global_lock:
            skus = list(self._products.keys())

        return {sku: self.get_stock_report(sku) for sku in skus}

    def get_system_summary(self) -> Dict[str, Any]:
        """Returns aggregated flash sale metrics and health summary."""
        reports = self.get_all_reports()
        total_initial = sum(r.initial_stock for r in reports.values())
        total_avail = sum(r.available for r in reports.values())
        total_reserved = sum(r.reserved for r in reports.values())
        total_sold = sum(r.sold for r in reports.values())

        with self._global_lock:
            total_res_count = len(self._reservations)
            active_res_count = sum(1 for r in self._reservations.values() if r.status == ReservationStatus.PENDING)
            confirmed_count = sum(1 for r in self._reservations.values() if r.status == ReservationStatus.CONFIRMED)
            cancelled_count = sum(1 for r in self._reservations.values() if r.status == ReservationStatus.CANCELLED)
            expired_count = sum(1 for r in self._reservations.values() if r.status == ReservationStatus.EXPIRED)

        return {
            "total_products": len(reports),
            "total_initial_stock": total_initial,
            "total_available": total_avail,
            "total_reserved": total_reserved,
            "total_sold": total_sold,
            "inventory_invariant_satisfied": (total_initial == total_avail + total_reserved + total_sold),
            "reservations_summary": {
                "total": total_res_count,
                "active": active_res_count,
                "confirmed": confirmed_count,
                "cancelled": cancelled_count,
                "expired": expired_count,
            },
            "audit_events_recorded": self.audit.get_count(),
        }

    # -------------------------------------------------------------------------
    # Stretch / Bonus Features: Waitlist Integration
    # -------------------------------------------------------------------------

    def join_waitlist(self, user_id: str, sku: str, quantity: int = 1) -> int:
        """
        Adds a user to the FIFO waitlist for a SKU when stock is depleted.
        Returns the user's 1-based position in queue.
        """
        if not user_id or not sku or quantity <= 0:
            raise ValidationError("Invalid waitlist parameters.")

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            if sku not in self._products:
                raise ProductNotFoundError(sku)

            entry_id = f"wl_{uuid.uuid4().hex[:8]}"
            pos = self.waitlist.join(entry_id, user_id, sku, quantity)

            self.audit.record(
                event_type="WAITLIST_JOINED",
                sku=sku,
                user_id=user_id,
                quantity=quantity,
                details={"position": pos},
            )
            return pos

    def _try_fulfill_waitlist(self, sku: str) -> Optional[Reservation]:
        """
        Attempts to allocate newly freed stock to the next eligible user in the waitlist.
        Must be called under SKU lock.
        """
        avail = self._available_stock.get(sku, 0)
        if avail <= 0:
            return None

        entry = self.waitlist.pop_next_eligible(sku, avail)
        if not entry:
            return None

        try:
            # Auto-reserve for the waitlisted user
            res = self.reserve(
                user_id=entry.user_id,
                sku=entry.sku,
                quantity=entry.requested_qty,
                ttl_seconds=self.default_ttl,
            )
            self.audit.record(
                event_type="WAITLIST_PROMOTED",
                sku=sku,
                user_id=entry.user_id,
                quantity=entry.requested_qty,
                reservation_id=res.reservation_id,
            )
            return res
        except (PurchaseLimitExceededError, InsufficientStockError):
            # If reservation fails (e.g. limit reached), user is skipped
            return None

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """Fetch a reservation by ID."""
        with self._global_lock:
            return self._reservations.get(reservation_id)
