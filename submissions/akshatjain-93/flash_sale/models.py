"""Lightweight, slot-optimized models for products, reservations, and stock reports."""

from dataclasses import dataclass, asdict
from enum import Enum
import time
from typing import Optional, Dict, Any


class ReservationStatus(str, Enum):
    """Lifecycle states of a stock reservation."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(slots=True)
class Product:
    """Product model with embedded counters for zero-overhead, single-lookup access."""
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
            raise ValueError(f"Stock for '{self.sku}' must be a non-negative integer.")
        if not isinstance(self.per_user_limit, int) or self.per_user_limit <= 0:
            raise ValueError(f"per_user_limit for '{self.sku}' must be a positive integer.")
        if self.price < 0.0:
            raise ValueError(f"Price for '{self.sku}' cannot be negative.")
        self.available = self.initial_stock


@dataclass(slots=True)
class Reservation:
    """Slot-optimized temporary stock reservation."""
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
    """Report snapshot with invariant validation."""
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


@dataclass(slots=True)
class AuditEvent:
    """Minimal audit event."""
    event_id: str
    event_type: str
    timestamp: float
    sku: Optional[str] = None
    user_id: Optional[str] = None
    quantity: Optional[int] = None
    reservation_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "sku": self.sku,
            "user_id": self.user_id,
            "quantity": self.quantity,
            "reservation_id": self.reservation_id,
            "details": self.details or {},
        }
