"""Pydantic schemas for rooms and bookings."""
from datetime import datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)


class Room(BaseModel):
    id: str
    name: str
    capacity: int = Field(gt=0)


class Recurrence(BaseModel):
    """Weekly recurrence. Exactly one of count / until must be given."""

    count: Optional[int] = Field(default=None, gt=0)
    until: Optional[datetime] = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "Recurrence":
        if (self.count is None) == (self.until is None):
            raise ValueError("recurrence requires exactly one of 'count' or 'until'")
        return self


class BookingBase(BaseModel):
    room_id: str
    organiser: str = Field(min_length=1, max_length=120)
    start: datetime
    end: datetime
    attendees: list[str] = Field(min_length=1)

    @field_validator("attendees")
    @classmethod
    def _strip_attendees(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for a in v:
            a = a.strip()
            if not a:
                raise ValueError("attendee names must be non-empty")
            if a not in seen:
                seen.append(a)
        return seen

    @model_validator(mode="after")
    def _valid_interval(self) -> "BookingBase":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        # Times must be within business hours and on whole minutes.
        for dt in (self.start, self.end):
            if dt.second or dt.microsecond:
                raise ValueError("times must be aligned to whole minutes")
            t = dt.time()
            if t < BUSINESS_START or t > BUSINESS_END:
                raise ValueError("bookings must fall between 09:00 and 18:00")
        return self


class BookingCreate(BookingBase):
    recurrence: Optional[Recurrence] = None


class BookingUpdate(BookingBase):
    recurrence: Optional[Recurrence] = None


class Booking(BookingBase):
    id: str
    recurrence: Optional[Recurrence] = None


class Occurrence(BaseModel):
    """A single expanded instance of a recurring series."""

    booking_id: str
    start: datetime
    end: datetime
    attendees: list[str]


class Conflict(BaseModel):
    occurrence_start: datetime
    occurrence_end: datetime
    conflicting_booking_id: str
    reason: Literal["overlap", "capacity"]


class ValidationResult(BaseModel):
    ok: bool
    occurrences: list[Occurrence] = []
    conflicts: list[Conflict] = []