"""Recurrence expansion for weekly recurring bookings.

A recurring :class:`~engine.models.Booking` is stored once and materialised on
demand.  An occurrence is created for every 7-day offset from the original
``start_time`` while the occurrence date ≤ ``recurrence_weekly_until``
(inclusive).

The weekday is determined by the *first* occurrence's date.  Subsequent
occurrences inherit the same time-of-day without any silent correction.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta

from .models import Booking


def _same_time(occurrence_date: date, template_dt: datetime) -> datetime:
    """Combine *occurrence_date* with the time from *template_dt*."""
    return datetime.combine(occurrence_date, template_dt.time())


def expand_occurrences(booking: Booking) -> list[Booking]:
    """Return every occurrence of *booking* within its recurrence window.

    Non-recurring bookings return a single-element list containing a shallow
    copy of *booking*.  Recurring bookings return one :class:`Booking` per week
    from the original date through ``recurrence_weekly_until`` (inclusive).

    The returned :class:`Booking` objects are shallow copies — they share
    ``attendees`` and other immutable fields, but ``start_time`` and
    ``end_time`` are adjusted per occurrence.
    """
    occurrences: list[Booking] = []
    template = copy.copy(booking)

    if not booking.is_recurring():
        return [template]

    assert booking.recurrence_weekly_until is not None
    step = timedelta(days=7)
    current = booking.start_time
    until_date = booking.recurrence_weekly_until

    while current.date() <= until_date:
        occ = copy.copy(booking)
        occ.start_time = current
        occ.end_time = current + (booking.end_time - booking.start_time)
        occurrences.append(occ)
        current = current + step

    return occurrences


def expand_to_date(booking: Booking, target_date: date) -> Booking | None:
    """Return the occurrence of *booking* that falls on *target_date*, or ``None``.

    For non-recurring bookings this returns the booking itself if it matches
    *target_date*.
    """
    if not booking.is_recurring():
        if booking.start_time.date() == target_date:
            return copy.copy(booking)
        return None

    assert booking.recurrence_weekly_until is not None

    # Must be same weekday
    if (target_date - booking.start_time.date()).days % 7 != 0:
        return None

    # Must be within the recurrence window
    if target_date < booking.start_time.date() or target_date > booking.recurrence_weekly_until:
        return None

    occ = copy.copy(booking)
    occ.start_time = datetime.combine(target_date, booking.start_time.time())
    occ.end_time = datetime.combine(target_date, booking.end_time.time())
    return occ