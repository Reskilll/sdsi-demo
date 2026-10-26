"""Custom exception hierarchy for the inventory reservation system."""


class InventoryError(Exception):
    """Base exception for all inventory reservation errors."""


class InvalidDataError(InventoryError):
    """Invalid input data — bad file, bad types, unknown SKU, etc."""


class InsufficientStockError(InventoryError):
    """Not enough available stock to fulfil the reservation."""


class PerUserLimitError(InventoryError):
    """User has reached or exceeded their per-SKU purchase limit."""


class ReservationNotFoundError(InventoryError):
    """No reservation exists for the given ID."""


class ReservationExpiredError(InventoryError):
    """The reservation has expired and cannot be actioned."""


class InvalidTransitionError(InventoryError):
    """The requested state transition is not allowed."""