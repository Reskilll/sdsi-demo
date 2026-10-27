"""
Pydantic v2 Schemas and Models for PS3 URL Shortener
Supports flexible input aliases and rich telemetry outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, AliasChoices, field_validator


class ShortenRequest(BaseModel):
    url: str = Field(
        ...,
        validation_alias=AliasChoices("url", "original_url", "long_url"),
        max_length=2048,
        description="Target long URL to shorten",
    )
    custom_alias: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("custom_alias", "alias", "custom_code"),
        max_length=32,
        description="Optional custom alias",
    )
    expires_at: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("expires_at", "expiry"),
        description="Optional ISO-8601 expiry timestamp",
    )
    ttl_seconds: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("ttl_seconds", "ttl", "expires_in"),
        ge=0,
        description="Optional time-to-live in seconds",
    )


class ShortenResponse(BaseModel):
    code: str
    short_code: str
    short_url: str
    url: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None
    escalated: bool = False


class DailyClickItem(BaseModel):
    date: str
    clicks: int


class StatsResponse(BaseModel):
    code: str
    short_code: str
    url: str
    original_url: str
    total_clicks: int
    clicks: int
    clicks_per_day: Dict[str, int]
    daily_clicks: List[DailyClickItem]
    last_accessed: Optional[str] = None
    last_accessed_at: Optional[str] = None
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False
    escalated: bool = False


class HealthResponse(BaseModel):
    status: str
    database: str
    total_links: int
    total_clicks: int
    chain_valid: bool


class AuditRecord(BaseModel):
    id: int
    timestamp: str
    event_type: str
    payload_json: str
    escalated: bool
    prev_hash: str
    curr_hash: str
