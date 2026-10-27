"""Domain models for the flash-sale inventory reservation system."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReservationStatus(str, Enum):
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    stock: int
    limit_per_user: int | None  # None = no per-user cap

    def __post_init__(self) -> None:
        if self.stock < 0:
            raise ValueError(f"stock must be >= 0, got {self.stock}")
        if self.limit_per_user is not None and self.limit_per_user < 1:
            raise ValueError(f"limit_per_user must be >= 1, got {self.limit_per_user}")
        if not self.sku.strip():
            raise ValueError("sku must be a non-empty string")

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        if not isinstance(data, dict):
            raise ValueError("entry must be an object")
        sku = data.get("sku")
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError("'sku' must be a non-empty string")
        name = data.get("name", sku)
        if not isinstance(name, str):
            raise ValueError("'name' must be a string")
        stock = data.get("stock")
        if isinstance(stock, bool) or not isinstance(stock, int):
            raise ValueError(f"'stock' must be an integer, got {type(stock).__name__}")
        if stock < 0:
            raise ValueError("'stock' must be >= 0")
        limit = data.get("limit_per_user")
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int):
                raise ValueError(f"'limit_per_user' must be an integer, got {type(limit).__name__}")
            if limit < 1:
                raise ValueError("'limit_per_user' must be >= 1")
        return cls(
            sku=sku.strip(),
            name=name.strip() or sku.strip(),
            stock=stock,
            limit_per_user=limit,
        )


@dataclass
class Reservation:
    id: str
    user: str
    sku: str
    qty: int
    created_at: float
    expires_at: float
    status: ReservationStatus = ReservationStatus.RESERVED