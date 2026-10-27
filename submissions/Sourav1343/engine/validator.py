"""Input validation for the booking engine.

This is the security boundary — every :class:`~engine.models.BookingRequest`
flows through here before any state is touched. Since PS2 is a SOC-adjacent
track the brief explicitly names untrusted-data handling, every function
treats input as adversarial.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Optional

from .models import Booking, BookingRequest, Conflict, Room

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum reasonable values to prevent resource exhaustion
MAX_ATTENDEES = 500
MAX_STRING_LEN = 500
MAX_RECURRENCE_WEEKS = 260  # 5 years
MIN_BOOKING_MINUTES = 1
ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$"
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Half-open interval overlap — back-to-back is **not** an overlap."""
    return a_start < b_end and b_start < a_end


def check_capacity(attendee_count: int, room: Room) -> Optional[str]:
    """Return an error string if *attendee_count* exceeds room capacity, else ``None``."""
    if attendee_count > room.capacity:
        return (
            f"attendee count {attendee_count} exceeds capacity {room.capacity} "
            f"for room {room.id} ({room.name})"
        )
    return None


# ---------------------------------------------------------------------------
# BookingRequest → Booking  (full validation)
# ---------------------------------------------------------------------------

def _validate_nonempty(value: str, field: str) -> Optional[str]:
    stripped = value.strip()
    if not stripped:
        return f"{field} must not be empty"
    if len(stripped) > MAX_STRING_LEN:
        return f"{field} exceeds maximum length {MAX_STRING_LEN}"
    return None


def _parse_datetime(raw: str, field: str) -> tuple[Optional[datetime], Optional[str]]:
    """Try to parse an ISO-8601-naive datetime.  Reject timezone offsets."""
    raw = raw.strip()
    # Ban timezone-aware strings
    if "+" in raw.split("T", 1)[-1] if "T" in raw else False:
        return None, f"{field} appears to contain a timezone offset; naive datetimes required"
    for suffix in ("Z", "z", " UTC"):
        if raw.rstrip().endswith(suffix):
            return None, f"{field} appears to contain a timezone suffix; naive datetimes required"

    # Try strict-ish ISO
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt, None
        except ValueError:
            continue
    return None, f"{field} is not a valid ISO-8601 naive datetime (e.g. 2026-10-27T09:00)"


def _parse_date(raw: str, field: str) -> tuple[Optional[date], Optional[str]]:
    """Parse ISO-8601 date.  Reject timezone annotations."""
    raw = raw.strip()
    if not ISO_DATE_RE.match(raw):
        return None, f"{field} is not a valid ISO-8601 date (e.g. 2026-10-27)"
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        return dt.date(), None
    except ValueError:
        return None, f"{field} is not a valid calendar date"


def _validate_attendees(attendees: list, field: str) -> Optional[str]:
    if not isinstance(attendees, list):
        return f"{field} must be a JSON array"
    if len(attendees) == 0:
        return f"{field} must not be empty"
    if len(attendees) > MAX_ATTENDEES:
        return f"{field} exceeds maximum size {MAX_ATTENDEES}"
    seen = set()
    duplicates: list[str] = []
    for i, name in enumerate(attendees):
        if not isinstance(name, str):
            return f"{field}[{i}] must be a string"
        stripped = name.strip()
        if not stripped:
            return f"{field}[{i}] must not be empty"
        if len(stripped) > MAX_STRING_LEN:
            return f"{field}[{i}] exceeds maximum length {MAX_STRING_LEN}"
        if stripped.lower() in seen:
            duplicates.append(stripped)
        else:
            seen.add(stripped.lower())
    if duplicates:
        return f"{field} contains duplicate names: {', '.join(duplicates)}"
    return None


def validate_booking_request(
    req: BookingRequest, rooms: dict[str, Room], existing_ids: set[str],
) -> list[str]:
    """Validate *req* holistically and return a list of human-readable errors.

    An empty return list means *req* is valid and can be converted into a
    :class:`~engine.models.Booking` with :func:`to_booking`.

    Checks performed:

    * Every string field is non-empty and below maximum length.
    * ``start_time`` and ``end_time`` are valid ISO-8601 naive datetimes.
    * ``end_time > start_time`` and duration ≥ 1 minute.
    * ``room_id`` references a known :class:`Room`.
    * ``attendees`` is a non-empty list of unique, non-empty names.
    * Attendee count does not exceed room capacity.
    * ``recurrence_weekly_until``, if present, is a valid date and the booking
      does not span midnight (no clear weekday anchor).
    * ``id`` is not already in use.
    """
    errors: list[str] = []

    # -- id --
    err = _validate_nonempty(req.id, "id")
    if err:
        errors.append(err)
    elif req.id.strip() in existing_ids:
        errors.append(f"booking id '{req.id.strip()}' already exists")

    # -- room_id --
    err = _validate_nonempty(req.room_id, "room_id")
    if err:
        errors.append(err)
    elif req.room_id.strip() not in rooms:
        errors.append(f"room '{req.room_id.strip()}' not found")

    # -- organiser --
    err = _validate_nonempty(req.organiser, "organiser")
    if err:
        errors.append(err)

    # -- times (naive local datetimes) --
    start, err_s = _parse_datetime(req.start_time, "start_time")
    end, err_e = _parse_datetime(req.end_time, "end_time")
    if err_s:
        errors.append(err_s)
    if err_e:
        errors.append(err_e)
    if start is not None and end is not None:
        if end <= start:
            errors.append("end_time must be after start_time")
        elif int((end - start).total_seconds()) / 60 < MIN_BOOKING_MINUTES:
            errors.append("booking duration must be at least 1 minute")

    # -- recurrence weekly_until --
    recurrence_date: Optional[date] = None
    if req.recurrence_weekly_until is not None:
        rdate, err_r = _parse_date(req.recurrence_weekly_until, "recurrence_weekly_until")
        if err_r:
            errors.append(err_r)
        elif start is not None and end is not None:
            rdate_typed: date = rdate  # type hint narrowing
            recurrence_date = rdate_typed
            if rdate_typed < start.date():
                errors.append(
                    "recurrence_weekly_until must be on or after the booking start date"
                )
            # Recurring bookings must not span midnight — each occurrence
            # repeats on the same weekday with the same times.
            if start.date() != end.date():
                errors.append(
                    "recurring bookings must not span midnight; "
                    "start_time and end_time must be on the same calendar date"
                )
            # Cap expansion to prevent DoS
            weeks = (rdate_typed - start.date()).days // 7
            if weeks > MAX_RECURRENCE_WEEKS:
                errors.append(
                    f"recurrence range exceeds maximum of {MAX_RECURRENCE_WEEKS} weeks"
                )

    # -- attendees --
    err = _validate_attendees(req.attendees, "attendees")
    if err:
        errors.append(err)

    # -- capacity (only if room known, attendees valid) --
    if req.room_id.strip() in rooms and isinstance(req.attendees, list) and len(req.attendees) > 0:
        room = rooms[req.room_id.strip()]
        err = check_capacity(len(req.attendees), room)
        if err:
            errors.append(err)

    return errors


def to_booking(req: BookingRequest) -> Booking:
    """Convert a *validated* :class:`BookingRequest` to a :class:`Booking`.

    Callers **must** run :func:`validate_booking_request` first — this function
    trusts its input.
    """
    start = _parse_datetime(req.start_time, "start_time")[0]
    end = _parse_datetime(req.end_time, "end_time")[0]
    assert start is not None and end is not None

    rdate: Optional[date] = None
    if req.recurrence_weekly_until is not None:
        rdate = _parse_date(req.recurrence_weekly_until, "recurrence_weekly_until")[0]

    return Booking(
        id=req.id.strip(),
        room_id=req.room_id.strip(),
        organiser=req.organiser.strip(),
        start_time=start,
        end_time=end,
        attendees=[a.strip() for a in req.attendees],
        recurrence_weekly_until=rdate,
    )


def assert_no_overlaps(
    candidate: Booking,
    occurrences: list[Booking],
    existing: list[Booking],
) -> list[Conflict]:
    """Check *occurrences* of *candidate* against *existing* bookings.

    Each candidate occurrence is compared against every existing booking's
    materialised representation on that occurrence's date — this ensures
    recurring-existing bookings block appropriate slots.

    Returns a (possibly empty) list of :class:`Conflict` objects — one per
    overlapping occurrence.
    """
    from .recurrence import expand_to_date

    conflicts: list[Conflict] = []
    for occ in occurrences:
        occ_date = occ.start_time.date()
        for ex in existing:
            if ex.id == candidate.id:
                continue  # skip self on update
            if ex.room_id != occ.room_id:
                continue
            # Materialise *ex* on occ_date so recurring existing bookings are
            # expanded to the correct date.
            ex_occ = expand_to_date(ex, occ_date)
            if ex_occ is None:
                continue  # existing booking doesn't occur on this date
            if overlaps(
                occ.start_time, occ.end_time,
                ex_occ.start_time, ex_occ.end_time,
            ):
                conflicts.append(
                    Conflict(
                        booking_id=candidate.id,
                        occurrence_date=occ_date,
                        reason=(
                            f"overlap with booking {ex.id} in room {occ.room_id} "
                            f"({occ.start_time.isoformat()}–{occ.end_time.isoformat()})"
                        ),
                    )
                )
                break  # one conflict per occurrence is enough
    return conflicts