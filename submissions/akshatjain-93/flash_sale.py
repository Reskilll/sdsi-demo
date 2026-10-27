"""
Flash Sale Inventory Management & Overselling Prevention Engine
Optimized for minimal space complexity (slots, embedded counters) and O(1) time complexity.
"""

from dataclasses import dataclass
from enum import Enum
import heapq
import itertools
import json
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Union, Callable, Any, Tuple


# =====================================================================
# Domain Exceptions
# =====================================================================

class FlashSaleError(Exception):
    def __init__(self, message: str, code: str = "FLASH_SALE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(FlashSaleError):
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class ProductNotFoundError(FlashSaleError):
    def __init__(self, sku: str):
        super().__init__(f"Product with SKU '{sku}' not found in inventory.", code="PRODUCT_NOT_FOUND")
        self.sku = sku


class InsufficientStockError(FlashSaleError):
    def __init__(self, sku: str, requested: int, available: int):
        super().__init__(f"Insufficient stock for SKU '{sku}': requested {requested}, available {available}.", code="INSUFFICIENT_STOCK")
        self.sku = sku
        self.requested = requested
        self.available = available


class PurchaseLimitExceededError(FlashSaleError):
    def __init__(self, user_id: str, sku: str, requested: int, current_reserved: int, current_purchased: int, limit: int):
        total = requested + current_reserved + current_purchased
        super().__init__(f"User '{user_id}' exceeded limit of {limit} for SKU '{sku}' (requested: {requested}, total: {total}).", code="PURCHASE_LIMIT_EXCEEDED")
        self.user_id = user_id
        self.sku = sku
        self.requested = requested
        self.current_reserved = current_reserved
        self.current_purchased = current_purchased
        self.limit = limit


class ReservationNotFoundError(FlashSaleError):
    def __init__(self, reservation_id: str, user_id: Optional[str] = None):
        user_info = f" for user '{user_id}'" if user_id else ""
        super().__init__(f"Reservation '{reservation_id}' not found{user_info}.", code="RESERVATION_NOT_FOUND")
        self.reservation_id = reservation_id
        self.user_id = user_id


class ReservationExpiredError(FlashSaleError):
    def __init__(self, reservation_id: str, expired_at: float):
        super().__init__(f"Reservation '{reservation_id}' has expired (at {expired_at:.2f}).", code="RESERVATION_EXPIRED")
        self.reservation_id = reservation_id
        self.expired_at = expired_at


class InvalidStateError(FlashSaleError):
    def __init__(self, reservation_id: str, current_state: str, attempted_action: str):
        super().__init__(f"Cannot {attempted_action} reservation '{reservation_id}' in '{current_state}' state.", code="INVALID_STATE")
        self.reservation_id = reservation_id
        self.current_state = current_state
        self.attempted_action = attempted_action


# =====================================================================
# Slot-Optimized Data Models
# =====================================================================

class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    initial_stock: int
    price: float = 0.0
    per_user_limit: int = 2
    available: int = 0
    reserved: int = 0
    sold: int = 0

    def __post_init__(self):
        if not self.sku or not isinstance(self.sku, str):
            raise ValueError("SKU must be a non-empty string.")
        if not isinstance(self.initial_stock, int) or self.initial_stock < 0:
            raise ValueError(f"Stock for '{self.sku}' must be non-negative integer.")
        if not isinstance(self.per_user_limit, int) or self.per_user_limit <= 0:
            raise ValueError(f"per_user_limit for '{self.sku}' must be positive.")
        if self.price < 0.0:
            raise ValueError("Price cannot be negative.")
        self.available = self.initial_stock


@dataclass(slots=True)
class Reservation:
    reservation_id: str
    user_id: str
    sku: str
    quantity: int
    created_at: float
    expires_at: float
    status: ReservationStatus = ReservationStatus.PENDING
    confirmed_at: Optional[float] = None
    cancelled_at: Optional[float] = None

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = time.time() if current_time is None else current_time
        return now >= self.expires_at

    def time_remaining(self, current_time: Optional[float] = None) -> float:
        now = time.time() if current_time is None else current_time
        return max(0.0, self.expires_at - now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "user_id": self.user_id,
            "sku": self.sku,
            "quantity": self.quantity,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "confirmed_at": self.confirmed_at,
            "cancelled_at": self.cancelled_at,
        }


@dataclass(slots=True)
class StockReport:
    sku: str
    name: str
    initial_stock: int
    available: int
    reserved: int
    sold: int

    def __post_init__(self):
        total = self.available + self.reserved + self.sold
        if total != self.initial_stock:
            raise ValueError(
                f"Invariant violation for '{self.sku}': avail({self.available}) + res({self.reserved}) + "
                f"sold({self.sold}) = {total} != initial({self.initial_stock})"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku,
            "name": self.name,
            "initial_stock": self.initial_stock,
            "available": self.available,
            "reserved": self.reserved,
            "sold": self.sold,
        }


# =====================================================================
# O(1) Space & Time Quota Limiter (M4)
# =====================================================================

class UserPurchaseLimiter:
    __slots__ = ("_lock", "_quotas")

    def __init__(self):
        self._lock = threading.Lock()
        self._quotas: Dict[Tuple[str, str], list] = {}  # (user_id, sku) -> [reserved, purchased]

    def get_active_reserved(self, user_id: str, sku: str) -> int:
        with self._lock:
            e = self._quotas.get((user_id, sku))
            return e[0] if e else 0

    def get_confirmed_purchased(self, user_id: str, sku: str) -> int:
        with self._lock:
            e = self._quotas.get((user_id, sku))
            return e[1] if e else 0

    def check_limit(self, user_id: str, sku: str, requested_qty: int, max_limit: int) -> None:
        with self._lock:
            e = self._quotas.get((user_id, sku))
            res = e[0] if e else 0
            pur = e[1] if e else 0
            if res + pur + requested_qty > max_limit:
                raise PurchaseLimitExceededError(user_id, sku, requested_qty, res, pur, max_limit)

    def record_reservation(self, user_id: str, sku: str, reservation_id: str, qty: int) -> None:
        with self._lock:
            k = (user_id, sku)
            if k in self._quotas:
                self._quotas[k][0] += qty
            else:
                self._quotas[k] = [qty, 0]

    def record_confirmation(self, user_id: str, sku: str, reservation_id: str, qty: int) -> None:
        with self._lock:
            k = (user_id, sku)
            if k in self._quotas:
                self._quotas[k][0] = max(0, self._quotas[k][0] - qty)
                self._quotas[k][1] += qty
            else:
                self._quotas[k] = [0, qty]

    def release_reservation(self, user_id: str, sku: str, reservation_id: str, qty: int = 0) -> int:
        with self._lock:
            k = (user_id, sku)
            if k in self._quotas:
                self._quotas[k][0] = max(0, self._quotas[k][0] - qty)
                if self._quotas[k][0] == 0 and self._quotas[k][1] == 0:
                    del self._quotas[k]
            return qty


# =====================================================================
# O(log N) Min-Heap TTL Sweeper (M2, M3)
# =====================================================================

class TTLSweeper:
    __slots__ = ("_callback", "_interval", "_time_func", "_heap", "_lock", "_stop_event", "_thread")

    def __init__(self, expire_callback: Callable[[str, str], None], sweep_interval: float = 0.5, time_func: Optional[Callable[[], float]] = None):
        self._callback = expire_callback
        self._interval = sweep_interval
        self._time_func = time_func or time.time
        self._heap: List[Tuple[float, str, str]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def schedule(self, reservation_id: str, sku: str, expires_at: float) -> None:
        with self._lock:
            heapq.heappush(self._heap, (expires_at, reservation_id, sku))

    def sweep_expired(self, current_time: Optional[float] = None) -> List[Tuple[str, str]]:
        now = self._time_func() if current_time is None else current_time
        expired_items: List[Tuple[str, str]] = []

        with self._lock:
            while self._heap and self._heap[0][0] <= now:
                _, res_id, sku = heapq.heappop(self._heap)
                expired_items.append((res_id, sku))

        for res_id, sku in expired_items:
            try:
                self._callback(res_id, sku)
            except Exception:
                pass

        return expired_items

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="TTLSweeperThread", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.sweep_expired()
            self._stop_event.wait(timeout=self._interval)


# =====================================================================
# Core Flash Sale Engine (M1 - M5)
# =====================================================================

class FlashSaleEngine:
    __slots__ = (
        "default_ttl", "default_per_user_limit", "_time_func",
        "_global_lock", "_sku_locks", "_products", "_reservations",
        "_counter", "limiter", "sweeper"
    )

    def __init__(
        self,
        inventory_source: Optional[Union[str, Path, List[Dict[str, Any]]]] = None,
        default_ttl: int = 120,
        default_per_user_limit: int = 2,
        auto_start_sweeper: bool = True,
        sweep_interval: float = 0.5,
        time_func: Optional[Callable[[], float]] = None,
    ):
        self.default_ttl = default_ttl
        self.default_per_user_limit = default_per_user_limit
        self._time_func = time_func or time.time

        self._global_lock = threading.RLock()
        self._sku_locks: Dict[str, threading.RLock] = {}
        self._products: Dict[str, Product] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._counter = itertools.count(1)

        self.limiter = UserPurchaseLimiter()
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
                raise ValidationError(f"Invalid inventory source: {type(inventory_source)}")

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

    # M1: Load inventory
    def load_inventory_file(self, filepath: Union[str, Path]) -> int:
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path.resolve()}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise ValidationError("JSON root must be list of products.")
        return self.load_inventory_data(data)

    def load_inventory_data(self, items: List[Dict[str, Any]]) -> int:
        if not isinstance(items, list):
            raise ValidationError("Items must be a list of dictionaries.")
        loaded = 0
        with self._global_lock:
            for item in items:
                sku = str(item.get("sku", "")).strip()
                if not sku:
                    raise ValidationError(f"Missing SKU in: {item}")
                stock = item.get("stock")
                if stock is None or not isinstance(stock, int) or stock < 0:
                    raise ValidationError(f"Invalid stock '{stock}' for SKU '{sku}'.")
                name = item.get("name", sku)
                price = float(item.get("price", 0.0))
                limit = item.get("per_user_limit", self.default_per_user_limit)
                if not isinstance(limit, int) or limit <= 0:
                    raise ValidationError(f"Invalid per_user_limit for SKU '{sku}'.")

                prod = Product(sku=sku, name=name, initial_stock=stock, price=price, per_user_limit=limit)
                sku_lock = self._get_sku_lock(sku)
                with sku_lock:
                    self._products[sku] = prod
                loaded += 1
        return loaded

    def _expire_single(self, res: Reservation, product: Optional[Product] = None) -> None:
        if res.status != ReservationStatus.PENDING:
            return
        res.status = ReservationStatus.EXPIRED
        prod = product or self._products.get(res.sku)
        if prod:
            prod.reserved -= res.quantity
            prod.available += res.quantity
        self.limiter.release_reservation(res.user_id, res.sku, res.reservation_id, res.quantity)

    def _handle_sweeper_expire(self, reservation_id: str, sku: str) -> None:
        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            res = self._reservations.get(reservation_id)
            if res and res.status == ReservationStatus.PENDING and res.is_expired(self._time_func()):
                self._expire_single(res, self._products.get(sku))

    # M2: Reserve stock with TTL
    def reserve(self, user_id: str, sku: str, quantity: int = 1, ttl_seconds: Optional[int] = None) -> Reservation:
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValidationError("user_id must be non-empty string.")
        user_id = user_id.strip()
        if not sku or not isinstance(sku, str) or not sku.strip():
            raise ValidationError("sku must be non-empty string.")
        sku = sku.strip()
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError(f"quantity must be positive int: {quantity}")
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        if not isinstance(ttl, int) or ttl <= 0:
            raise ValidationError(f"ttl must be positive int: {ttl_seconds}")

        sku_lock = self._get_sku_lock(sku)
        with sku_lock:
            product = self._products.get(sku)
            if not product:
                raise ProductNotFoundError(sku)

            # M4 Quota check
            self.limiter.check_limit(user_id, sku, quantity, product.per_user_limit)

            # Stock check
            if product.available < quantity:
                raise InsufficientStockError(sku, quantity, product.available)

            product.available -= quantity
            product.reserved += quantity

            now = self._time_func()
            res_id = f"res_{time.time_ns():x}_{next(self._counter)}"
            res = Reservation(
                reservation_id=res_id,
                user_id=user_id,
                sku=sku,
                quantity=quantity,
                created_at=now,
                expires_at=now + ttl,
                status=ReservationStatus.PENDING,
            )
            self._reservations[res_id] = res
            self.limiter.record_reservation(user_id, sku, res_id, quantity)
            self.sweeper.schedule(res_id, sku, res.expires_at)
            return res

    # M3: Confirm permanently into sold
    def confirm(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        if not reservation_id or not isinstance(reservation_id, str):
            raise ValidationError("reservation_id must be string.")

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
            return res

    # M3: Cancel releases stock
    def cancel(self, reservation_id: str, user_id: Optional[str] = None) -> Reservation:
        if not reservation_id or not isinstance(reservation_id, str):
            raise ValidationError("reservation_id must be string.")

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
            return res

    def release_expired(self) -> List[str]:
        expired = self.sweeper.sweep_expired()
        return [res_id for res_id, _ in expired]

    # M5: Real-time reporting
    def get_stock_report(self, sku: str) -> StockReport:
        if not sku or not isinstance(sku, str):
            raise ValidationError("sku must be non-empty string.")
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


FlashSaleManager = FlashSaleEngine


if __name__ == "__main__":
    sample = [{"sku": "FLASH-PHONE", "name": "Phone", "stock": 5, "price": 999.0, "per_user_limit": 2}]
    with FlashSaleEngine(inventory_source=sample, default_ttl=3) as engine:
        print("[M1] Loaded.")
        r = engine.reserve("user_1", "FLASH-PHONE", 2)
        print(f"[M2] Reserved: {r.reservation_id}")
        rep = engine.get_stock_report("FLASH-PHONE")
        print(f"[M5] Avail={rep.available}, Res={rep.reserved}, Sold={rep.sold}")
        engine.confirm(r.reservation_id, "user_1")
        print("[M3] Confirmed.")
        rep = engine.get_stock_report("FLASH-PHONE")
        print(f"[M5] Avail={rep.available}, Res={rep.reserved}, Sold={rep.sold}")
