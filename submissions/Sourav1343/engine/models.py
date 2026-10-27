"""Data models for the Meeting Room Booking Engine.

All fields on :class:`BookingRequest` are treated as *untrusted* input. They are
validated in :mod:`engine.validator` before a :class:`Booking` is constructed.
This module intentionally contains no logic beyond pure data containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class Room:
    """A bookable room with a fixed capacity."""

    id: str
    name: str
    capacity: int


@dataclass
class BookingRequest:
    """Untrusted, not-yet-validated booking payload.

    ``start_time``/``end_time`` are ISO-8601 strings (naive local datetime).
    ``recurrence_weekly_until`` is an optional ISO-8601 date string that, when
    present, turns the booking into a weekly recurring series.
    """

    id: str
    room_id: str
    organiser: str
    start_time: str
    end_time: str
    attendees: list[str]
    recurrence_weekly_until: Optional[str] = None


@dataclass
class Booking:
    """A fully validated booking stored in the engine.

    Recurring bookings are stored once with a non-``None``
    ``recurrence_weekly_until``; individual occurrences are materialised on
    demand by :mod:`engine.recurrence`.
    """

    id: str
    room_id: str
    organiser: str
    start_time: datetime
    end_time: datetime
    attendees: list[str]
    recurrence_weekly_until: Optional[date] = None

    def is_recurring(self) -> bool:
        return self.recurrence_weekly_until is not None

    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() // 60)

    def attendee_count(self) -> int:
        return len(self.attendees)


@dataclass(frozen=True)
class Slot:
    """A free interval offered by :func:`engine.finder.find_available_slot`."""

    room: Room
    start: datetime
    end: datetime


@dataclass
class Conflict:
    """A single reason a booking (or one of its occurrences) was rejected."""

    booking_id: str
    occurrence_date: date
    reason: str


@dataclass
class BookingResult:
    """Result of a create/update attempt.

    ``success`` is ``True`` only when the booking was fully applied. On failure
    ``conflicts`` (M5) and/or ``errors`` (validation) describe the cause and no
    state is mutated.
    """

    success: bool
    booking: Optional[Booking] = None
    conflicts: list[Conflict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
