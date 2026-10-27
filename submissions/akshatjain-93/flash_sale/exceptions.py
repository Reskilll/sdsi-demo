"""Domain-specific exceptions for the flash sale inventory management system."""

from typing import Optional


class FlashSaleError(Exception):
    """Base exception for all flash sale operations."""
    def __init__(self, message: str, code: str = "FLASH_SALE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(FlashSaleError):
    """Raised when input parameters fail validation checks."""
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class ProductNotFoundError(FlashSaleError):
    """Raised when a requested product SKU does not exist."""
    def __init__(self, sku: str):
        super().__init__(f"Product with SKU '{sku}' not found in inventory.", code="PRODUCT_NOT_FOUND")
        self.sku = sku


class InsufficientStockError(FlashSaleError):
    """Raised when the requested quantity exceeds currently available stock."""
    def __init__(self, sku: str, requested: int, available: int):
        super().__init__(
            f"Insufficient stock for SKU '{sku}': requested {requested}, but only {available} available.",
            code="INSUFFICIENT_STOCK",
        )
        self.sku = sku
        self.requested = requested
        self.available = available


class PurchaseLimitExceededError(FlashSaleError):
    """Raised when a user attempts to reserve or purchase beyond their allowed quota."""
    def __init__(
        self,
        user_id: str,
        sku: str,
        requested: int,
        current_reserved: int,
        current_purchased: int,
        limit: int,
    ):
        total_attempted = requested + current_reserved + current_purchased
        super().__init__(
            f"User '{user_id}' exceeded limit of {limit} for SKU '{sku}'. "
            f"Already reserved: {current_reserved}, already purchased: {current_purchased}, "
            f"requested: {requested} (total: {total_attempted}).",
            code="PURCHASE_LIMIT_EXCEEDED",
        )
        self.user_id = user_id
        self.sku = sku
        self.requested = requested
        self.current_reserved = current_reserved
        self.current_purchased = current_purchased
        self.limit = limit


class ReservationNotFoundError(FlashSaleError):
    """Raised when a reservation cannot be found or does not belong to the user."""
    def __init__(self, reservation_id: str, user_id: Optional[str] = None):
        user_info = f" for user '{user_id}'" if user_id else ""
        super().__init__(
            f"Reservation '{reservation_id}' not found{user_info}.",
            code="RESERVATION_NOT_FOUND",
        )
        self.reservation_id = reservation_id
        self.user_id = user_id


class ReservationExpiredError(FlashSaleError):
    """Raised when attempting an operation on an expired reservation."""
    def __init__(self, reservation_id: str, expired_at: float):
        super().__init__(
            f"Reservation '{reservation_id}' has expired (expired at timestamp {expired_at:.2f}).",
            code="RESERVATION_EXPIRED",
        )
        self.reservation_id = reservation_id
        self.expired_at = expired_at


class InvalidStateError(FlashSaleError):
    """Raised when an operation is invalid for the reservation's current state."""
    def __init__(self, reservation_id: str, current_state: str, attempted_action: str):
        super().__init__(
            f"Cannot {attempted_action} reservation '{reservation_id}' in '{current_state}' state.",
            code="INVALID_STATE",
        )
        self.reservation_id = reservation_id
        self.current_state = current_state
        self.attempted_action = attempted_action
