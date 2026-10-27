"""Find-slot algorithm (M4).

Given a duration, attendee count, and date, returns the globally earliest
available room and start time within business hours (09:00–18:00).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from .models import Room, Slot
from .recurrence import expand_to_date


BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
STEP = timedelta(minutes=1)


def find_available_slot(
    store: "InMemoryStore",  # noqa: F821  # forward reference
    duration_minutes: int,
    attendee_count: int,
    target_date: date,
    business_start: time = BUSINESS_START,
    business_end: time = BUSINESS_END,
) -> Optional[Slot]:
    """Return the globally earliest :class:`Slot`, or ``None``.

    Parameters
    ----------
    store:
        The booking store (provides room catalogue + existing bookings).
    duration_minutes:
        Required booking duration in minutes.  Must be ≥ 1.
    attendee_count:
        Number of attendees — filters rooms by capacity.
    target_date:
        Which date to search.
    business_start / business_end:
        Inclusive start / end of the operating window.  A slot that *ends* at
        ``business_end`` is valid; a slot that would extend beyond it is not.

    Returns
    -------
    Slot or None
        The earliest slot found, or ``None`` when no room can accommodate the
        request on *target_date*.
    """
    if duration_minutes < 1:
        return None

    duration_delta = timedelta(minutes=duration_minutes)
    rooms = store.get_rooms_by_capacity(attendee_count)

    if not rooms:
        return None

    end_boundary = datetime.combine(target_date, business_end)
    current = datetime.combine(target_date, business_start)

    while current + duration_delta <= end_boundary:
        slot_end = current + duration_delta
        for room in rooms:
            if _is_free(store, room, current, slot_end, target_date):
                return Slot(room=room, start=current, end=slot_end)
        current += STEP

    return None


def _is_free(
    store: "InMemoryStore",  # noqa: F821
    room: Room,
    start: datetime,
    end: datetime,
    target_date: date,
) -> bool:
    """Check whether a candidate interval is free for *room* on *target_date*.

    Considers both one-off bookings and expanded recurring occurrences.
    """
    for booking in store.bookings_for_date(target_date):
        if booking.room_id != room.id:
            continue
        from .validator import overlaps
        if overlaps(booking.start_time, booking.end_time, start, end):
            return False
    return True