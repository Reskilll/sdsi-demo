"""Booking domain logic: creation, conflicts, recurrence and slot search."""
import itertools
import uuid
from datetime import date, datetime, time, timedelta

from .models import (
    BUSINESS_END,
    BUSINESS_START,
    Booking,
    BookingCreate,
    Conflict,
    Occurrence,
    Recurrence,
    Room,
    ValidationResult,
)
from .store import Store


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Half-open interval overlap — back-to-back boundaries do not collide."""
    return a_start < b_end and b_start < a_end


def expand(base: Booking) -> list[Occurrence]:
    """Expand a booking into its concrete occurrences (recurring or single)."""
    if base.recurrence is None:
        return [
            Occurrence(
                booking_id=base.id,
                start=base.start,
                end=base.end,
                attendees=base.attendees,
            )
        ]
    rec: Recurrence = base.recurrence
    week = timedelta(weeks=1)
    anchor = base.start
    if rec.count is not None:
        limit = rec.count
    else:
        # Include the occurrence that starts on (or before) the 'until' date.
        limit = max(1, (rec.until.date() - anchor.date()).days // 7 + 1)
    return [
        Occurrence(
            booking_id=base.id,
            start=anchor + week * i,
            end=base.end + week * i,
            attendees=base.attendees,
        )
        for i in range(limit)
    ]


class BookingService:
    def __init__(self, store: Store) -> None:
        self._store = store

    def existing(self, booking_id: str) -> Booking | None:
        return self._store.get_booking(booking_id)

    def list(self) -> list[Booking]:
        return self._store.list_bookings()

    def create(self, data: BookingCreate) -> Booking:
        booking = Booking(
            id=uuid.uuid4().hex[:12],
            room_id=data.room_id,
            organiser=data.organiser,
            start=data.start,
            end=data.end,
            attendees=data.attendees,
            recurrence=data.recurrence,
        )
        self._store.save(booking)
        return booking

    def validate(self, base: Booking, exclude_id: str | None = None) -> ValidationResult:
        """Validate a (possibly recurring) booking: capacity per room + overlaps.

        For a single occurrence, one booking's one conflict maps to one
        ValidationResult.conflicts entry. For recurring, every occurrence is
        expanded and each conflict is reported with its own occurrence window.
        """
        room = self._store.get_room(base.room_id)
        if room is None:
            raise KeyError(base.room_id)

        occurrences = expand(base)
        conflicts: list[Conflict] = []

        if len(base.attendees) > room.capacity:
            for occ in occurrences:
                conflicts.append(Conflict(
                    occurrence_start=occ.start,
                    occurrence_end=occ.end,
                    conflicting_booking_id=base.id,
                    reason="capacity",
                ))
            return ValidationResult(ok=False, occurrences=occurrences, conflicts=conflicts)

        others = [b for b in self._store.list_bookings() if b.room_id == base.room_id]
        for occ in occurrences:
            for other in others:
                if other.id == exclude_id or other.id == base.id:
                    continue
                for other_occ in expand(other):
                    if _overlap(occ.start, occ.end, other_occ.start, other_occ.end):
                        conflicts.append(Conflict(
                            occurrence_start=occ.start,
                            occurrence_end=occ.end,
                            conflicting_booking_id=other.id,
                            reason="overlap",
                        ))
                        break  # one conflicting booking per occurrence is enough

        return ValidationResult(ok=not conflicts, occurrences=occurrences, conflicts=conflicts)

    def delete(self, booking_id: str) -> bool:
        return self._store.delete(booking_id)

    def find_slot(
        self, duration_mins: int, attendees: int, day: date
    ) -> tuple[Room, datetime] | None:
        """Earliest free room+start on `day`; business hours 09:00–18:00."""
        day_start = datetime.combine(day, BUSINESS_START)
        day_end = datetime.combine(day, BUSINESS_END)
        if duration_mins <= 0 or day_start + timedelta(minutes=duration_mins) > day_end:
            return None
        candidates = self._store.rooms_for_capacity(attendees)
        slot = day_start
        step = timedelta(minutes=duration_mins)
        while slot + step <= day_end:
            for room in candidates:
                if all(
                    not _overlap(slot, slot + step, occ.start, occ.end)
                    for other in self._store.list_bookings()
                    if other.room_id == room.id
                    for occ in expand(other)
                ):
                    return room, slot
            slot += step
        return None