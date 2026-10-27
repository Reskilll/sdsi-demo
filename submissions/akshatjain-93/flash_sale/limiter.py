"""Per-user purchase and reservation quota tracker."""

import threading
from typing import Dict, Tuple
from .exceptions import PurchaseLimitExceededError


class UserPurchaseLimiter:
    """
    Enforces per-user purchase limits per SKU across both pending reservations
    and permanently confirmed purchases.
    
    A user cannot hold active reservations + confirmed purchases that exceed
    the product's per_user_limit.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # (user_id, sku) -> {reservation_id: quantity}
        self._active_reservations: Dict[Tuple[str, str], Dict[str, int]] = {}
        # (user_id, sku) -> total confirmed quantity
        self._confirmed_purchases: Dict[Tuple[str, str], int] = {}

    def get_active_reserved(self, user_id: str, sku: str) -> int:
        """Returns total active quantity currently reserved by user for SKU."""
        with self._lock:
            user_sku_res = self._active_reservations.get((user_id, sku), {})
            return sum(user_sku_res.values())

    def get_confirmed_purchased(self, user_id: str, sku: str) -> int:
        """Returns total confirmed quantity purchased by user for SKU."""
        with self._lock:
            return self._confirmed_purchases.get((user_id, sku), 0)

    def get_total_committed(self, user_id: str, sku: str) -> int:
        """Returns active reservations + confirmed purchases for user and SKU."""
        with self._lock:
            user_sku_res = self._active_reservations.get((user_id, sku), {})
            reserved = sum(user_sku_res.values())
            purchased = self._confirmed_purchases.get((user_id, sku), 0)
            return reserved + purchased

    def check_limit(self, user_id: str, sku: str, requested_qty: int, max_limit: int) -> None:
        """
        Validates that adding requested_qty does not violate the user's limit.
        Raises PurchaseLimitExceededError if it would exceed max_limit.
        """
        with self._lock:
            user_sku_res = self._active_reservations.get((user_id, sku), {})
            reserved = sum(user_sku_res.values())
            purchased = self._confirmed_purchases.get((user_id, sku), 0)
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
        """Registers a newly created pending reservation under user's quota."""
        with self._lock:
            key = (user_id, sku)
            if key not in self._active_reservations:
                self._active_reservations[key] = {}
            self._active_reservations[key][reservation_id] = qty

    def record_confirmation(self, user_id: str, sku: str, reservation_id: str, qty: int) -> None:
        """
        Transfers quantity from active reservation to confirmed purchase count.
        """
        with self._lock:
            key = (user_id, sku)
            if key in self._active_reservations:
                self._active_reservations[key].pop(reservation_id, None)
                if not self._active_reservations[key]:
                    del self._active_reservations[key]
            self._confirmed_purchases[key] = self._confirmed_purchases.get(key, 0) + qty

    def release_reservation(self, user_id: str, sku: str, reservation_id: str) -> int:
        """
        Removes an active reservation (due to cancel or expiry) without increasing purchased count.
        Returns the quantity that was released.
        """
        with self._lock:
            key = (user_id, sku)
            released_qty = 0
            if key in self._active_reservations:
                released_qty = self._active_reservations[key].pop(reservation_id, 0)
                if not self._active_reservations[key]:
                    del self._active_reservations[key]
            return released_qty

    def reset(self) -> None:
        """Resets all limits (useful for testing)."""
        with self._lock:
            self._active_reservations.clear()
            self._confirmed_purchases.clear()
