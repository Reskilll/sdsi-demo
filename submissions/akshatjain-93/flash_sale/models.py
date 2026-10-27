"""Data models for products, reservations, stock reports, and audit events."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Optional, Dict, Any


class ReservationStatus(str, Enum):
    """Lifecycle states of a stock reservation."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class Product:
    """Represents a product item in the inventory."""
    sku: str
    name: str
    initial_stock: int
    price: float = 0.0
    per_user_limit: int = 2

    def __post_init__(self):
        if not self.sku or not isinstance(self.sku, str):
            raise ValueError("SKU must be a non-empty string.")
        if not isinstance(self.initial_stock, int) or self.initial_stock < 0:
            raise ValueError(f"Stock for '{self.sku}' must be a non-negative integer.")
        if not isinstance(self.per_user_limit, int) or self.per_user_limit <= 0:
            raise ValueError(f"per_user_limit for '{self.sku}' must be a positive integer.")
        if self.price < 0.0:
            raise ValueError(f"Price for '{self.sku}' cannot be negative.")


@dataclass
class Reservation:
    """Represents a temporary stock hold for a user."""
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
        """Returns True if current time has passed expiry timestamp."""
        now = time.time() if current_time is None else current_time
        return now >= self.expires_at

    def time_remaining(self, current_time: Optional[float] = None) -> float:
        """Returns seconds remaining before expiration (min 0.0)."""
        now = time.time() if current_time is None else current_time
        return max(0.0, self.expires_at - now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class StockReport:
    """Snapshot of stock counts for a specific SKU."""
    sku: str
    name: str
    initial_stock: int
    available: int
    reserved: int
    sold: int

    def __post_init__(self):
        # Strict consistency invariant check
        total_accounted = self.available + self.reserved + self.sold
        if total_accounted != self.initial_stock:
            raise ValueError(
                f"Invariant violation for SKU '{self.sku}': "
                f"available ({self.available}) + reserved ({self.reserved}) + sold ({self.sold}) = "
                f"{total_accounted} != initial_stock ({self.initial_stock})"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class AuditEvent:
    """Immutable audit record for tracking flash sale transactions."""
    event_id: str
    event_type: str
    timestamp: float
    sku: Optional[str] = None
    user_id: Optional[str] = None
    quantity: Optional[int] = None
    reservation_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

