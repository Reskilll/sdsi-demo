"""High-performance, O(1) space & time per-user quota tracker."""

import threading
from typing import Dict, Tuple
from .exceptions import PurchaseLimitExceededError


class UserPurchaseLimiter:
    """
    Enforces per-user purchase limits per SKU in O(1) time and minimal memory.
    Tracks [reserved_count, purchased_count] directly per (user_id, sku) pair.
    """

    __slots__ = ("_lock", "_quotas")

    def __init__(self):
        self._lock = threading.Lock()
        # (user_id, sku) -> [reserved_count, purchased_count]
        self._quotas: Dict[Tuple[str, str], list] = {}

    def get_active_reserved(self, user_id: str, sku: str) -> int:
        with self._lock:
            entry = self._quotas.get((user_id, sku))
            return entry[0] if entry else 0

    def get_confirmed_purchased(self, user_id: str, sku: str) -> int:
        with self._lock:
            entry = self._quotas.get((user_id, sku))
            return entry[1] if entry else 0

    def get_total_committed(self, user_id: str, sku: str) -> int:
        with self._lock:
            entry = self._quotas.get((user_id, sku))
            return (entry[0] + entry[1]) if entry else 0

    def check_limit(self, user_id: str, sku: str, requested_qty: int, max_limit: int) -> None:
        """O(1) limit check avoiding any list scans or dictionary allocations."""
        with self._lock:
            entry = self._quotas.get((user_id, sku))
            reserved = entry[0] if entry else 0
            purchased = entry[1] if entry else 0
            if reserved + purchased + requested_qty > max_limit:
                raise PurchaseLimitExceededError(
                    user_id=user_id,
                    sku=sku,
                    requested=requested_qty,
                    current_reserved=reserved,
                    current_purchased=purchased,
                    limit=max_limit,
                )

    def record_reservation(self, user_id: str, sku: str, reservation_id: str, qty: int) -> None:
        """O(1) quota increment on reservation."""
        with self._lock:
            key = (user_id, sku)
            if key in self._quotas:
                self._quotas[key][0] += qty
            else:
                self._quotas[key] = [qty, 0]

    def record_confirmation(self, user_id: str, sku: str, reservation_id: str, qty: int) -> None:
        """O(1) transition from reserved to purchased."""
        with self._lock:
            key = (user_id, sku)
            if key in self._quotas:
                self._quotas[key][0] = max(0, self._quotas[key][0] - qty)
                self._quotas[key][1] += qty
            else:
                self._quotas[key] = [0, qty]

    def release_reservation(self, user_id: str, sku: str, reservation_id: str, qty: int = 0) -> int:
        """O(1) quota release on cancellation or expiry."""
        with self._lock:
            key = (user_id, sku)
            if key in self._quotas:
                self._quotas[key][0] = max(0, self._quotas[key][0] - qty)
                # Clean up empty entries to preserve space
                if self._quotas[key][0] == 0 and self._quotas[key][1] == 0:
                    del self._quotas[key]
            return qty

    def reset(self) -> None:
        with self._lock:
            self._quotas.clear()
