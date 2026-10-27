"""Data models for the inventory reservation system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict


class ReservationState(str, Enum):
    active = "active"
    confirmed = "confirmed"
    cancelled = "cancelled"
    expired = "expired"


@dataclass(frozen=True)
class Product:
    """Blueprint loaded from inventory.json — immutable after construction."""

    sku: str
    name: str
    total: int
    per_user_limit: int
    ttl_seconds: int = 120


@dataclass
class ReservationRecord:
    """A single reservation's mutable state, held in the engine's datastore."""

    reservation_id: str
    sku: str
    user_id: str
    qty: int
    state: ReservationState = ReservationState.active
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=120))

    def has_expired(self, now: datetime | None = None) -> bool:
        if self.state != ReservationState.active:
            return False
        return (now or datetime.now(timezone.utc)) >= self.expires_at


@dataclass
class UserSkuState:
    """Per-user-per-SKU counters, built from active reservations + confirms."""

    reserved: int = 0
    sold: int = 0

    @property
    def total_held(self) -> int:
        return self.reserved + self.sold


@dataclass
class ProductState:
    """Runtime mutable counters for a single product."""

    total: int
    reserved: int = 0
    sold: int = 0

    @property
    def available(self) -> int:
        return self.total - self.reserved - self.sold

    @property
    def invariant_holds(self) -> bool:
        return self.reserved + self.sold <= self.total


def new_id() -> str:
    """Short, URL-safe unique reservation ID."""
    return uuid.uuid4().hex[:16]