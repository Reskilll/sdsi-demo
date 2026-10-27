"""
Pydantic request/response schemas for the FastAPI layer.

All models carry field-level validation so bad input never reaches the engine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ────────────────────────────────────────────────────────────────────
# Request schemas
# ────────────────────────────────────────────────────────────────────


class ReserveRequest(BaseModel):
    """M2: Reserve stock for a user."""

    sku: str = Field(..., min_length=1, max_length=64, description="Product SKU")
    user_id: str = Field(..., min_length=1, max_length=128, description="User identifier")
    quantity: int = Field(..., ge=1, le=100000, description="Quantity to reserve (>=1)")
    idempotency_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Client-supplied idempotency key to prevent duplicate reservations",
    )

    @field_validator("sku", "user_id")
    @classmethod
    def no_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Value cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None  # treat whitespace-only as absent
        return v


class ConfirmCancelRequest(BaseModel):
    """M3: Confirm or cancel a reservation."""

    reservation_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Reservation ID returned by /reserve",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Client-supplied idempotency key",
    )

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        return v


class CancelRequest(ConfirmCancelRequest):
    """Same shape as confirm — separate type for readability."""
    pass


# ────────────────────────────────────────────────────────────────────
# Response schemas
# ────────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ReservationResponse(BaseModel):
    reservation_id: str
    sku: str
    user_id: str
    quantity: int
    state: str
    expires_at_iso: Optional[str] = None  # wall-clock estimate for display


class SkuReportResponse(BaseModel):
    sku: str
    total_stock: int
    sold: int
    reserved: int
    available: int
    is_sold_out: bool


class InventoryReportResponse(BaseModel):
    products: List[SkuReportResponse]