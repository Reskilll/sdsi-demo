"""
Data models for the Inventory Reservation System.

Separated from storage so every layer can import types without
creating circular imports or dragging in lock primitives.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

# ── Enums ───────────────────────────────────────────────────────────


class ReservationState(str, Enum):
    """Lifecycle of a single reservation.

    ┌─────────┐   confirm    ┌──────┐
    │ RESERVED ├───────────► │ SOLD │
    └──┬───▲──┘              └──────┘
       │   │
       │   │  cancel / expire
       │   │
       ▼   │
    ┌──────────┐
    │ RELEASED │  (terminal)
    └──────────┘

    An idempotent confirm/cancel on a terminal reservation is a no-op,
    not an error — we just return the terminal state.
    """

    RESERVED = "reserved"
    SOLD = "sold"
    RELEASED = "released"


class ErrorCode(str, Enum):
    """Strongly-typed error codes for API responses and telemetry."""

    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    USER_LIMIT_EXCEEDED = "USER_LIMIT_EXCEEDED"
    RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
    RESERVATION_ALREADY_TERMINAL = "RESERVATION_ALREADY_TERMINAL"
    SKU_NOT_FOUND = "SKU_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"


# ── Domain value-objects ────────────────────────────────────────────


@dataclass(frozen=True)
class Product:
    """Immutable snapshot of a product loaded from inventory.json."""

    sku: str
    name: str
    total_stock: int
    per_user_limit: int

    def validate(self) -> None:
        if self.total_stock < 0:
            raise ValueError(f"total_stock must be >= 0, got {self.total_stock}")
        if self.per_user_limit < 1:
            raise ValueError(f"per_user_limit must be >= 1, got {self.per_user_limit}")
        if not self.sku.strip():
            raise ValueError("sku cannot be empty")
        if not self.name.strip():
            raise ValueError("name cannot be empty")


@dataclass(frozen=True)
class ReservationRecord:
    """Snapshot returned to callers — threads can read these safely."""

    reservation_id: str
    sku: str
    user_id: str
    quantity: int
    state: ReservationState
    created_at: float  # monotonic clock (time.monotonic)
    expires_at: float  # monotonic clock
    confirmed_at: Optional[float] = None
    released_at: Optional[float] = None


@dataclass(frozen=True)
class SkuReport:
    """Real-time stock counters for one SKU (M5)."""

    sku: str
    total_stock: int
    sold: int
    reserved: int
    available: int  # total_stock - sold - reserved

    @property
    def is_sold_out(self) -> bool:
        return self.available <= 0


@dataclass
class IdempotencyRecord:
    """Cached response for a previously-completed idempotency key."""

    response: dict
    created_at: float  # wall-clock time
    ttl_seconds: float


# ── Config ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SystemConfig:
    """Runtime configuration — read once at startup, never mutated."""

    reservation_ttl_seconds: float = 120.0
    sweeper_interval_seconds: float = 1.0
    idempotency_ttl_seconds: float = 86_400.0  # 24 h