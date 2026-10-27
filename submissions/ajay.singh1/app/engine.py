"""Booking engine — pure business logic, no database or HTTP concerns."""
from datetime import date, datetime, time, timedelta
from .rooms import room_exists, room_capacity


OVERLAP_ERROR = "Room is already booked during the requested time slot."
ROOM_NOT_FOUND = "Room does not exist."
CAPACITY_EXCEEDED = "Attendee count exceeds room capacity."


def _get_config():
    import app.config
    return app.config


def validate_booking_input(
    room: str,
    attendee_count: int,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Raise ValueError if booking input is invalid."""
    if not room_exists(room):
        raise ValueError(ROOM_NOT_FOUND)
    cap = room_capacity(room)
    if attendee_count > cap:
        raise ValueError(f"{CAPACITY_EXCEEDED} (room: {room}, capacity: {cap}, requested: {attendee_count})")
    if start_time >= end_time:
        raise ValueError("start_time must be before end_time")
    if start_time.date() != end_time.date():
        raise ValueError("start_time and end_time must be on the same date")


def generate_recurrence_dates(start: date, end: date) -> list[date]:
    """Generate weekly dates from start to end inclusive.

    Returns dates on the same weekday as `start`, every 7 days, bounded by end and MAX_RECURRENCE_OCCURRENCES.
    """
    cfg = _get_config()
    if start > end:
        return []
    dates: list[date] = []
    current = start
    while current <= end and len(dates) < cfg.MAX_RECURRENCE_OCCURRENCES:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def build_occurrence_datetimes(
    template_start: datetime,
    template_end: datetime,
    target_date: date,
) -> tuple[datetime, datetime]:
    """Produce start/end datetimes for an occurrence on target_date,
    preserving the time-of-day from the template.
    """
    start = template_start.time()
    end = template_end.time()
    dt_start = datetime.combine(target_date, start)
    dt_end = datetime.combine(target_date, end)
    return dt_start, dt_end


def find_earliest_slot(
    target_date: date,
    duration_minutes: int,
    attendee_count: int,
    rooms: dict[str, int],  # room_name -> capacity
    bookings_for_date: list[dict],  # bookings sorted by start_time
) -> tuple[str | None, datetime | None, datetime | None]:
    """Find the earliest available room and time for the given date.

    Rules:
    - Only consider rooms with capacity >= attendee_count.
    - Only consider slots within [09:00, 18:00].
    - A slot [start, start+duration) must not overlap any existing booking.
    - Deterministic tie-breaking: earliest start_time; if tied, room name alphabetically.

    Returns (room, start_time, end_time) or (None, None, None).
    """
    cfg = _get_config()

    # Filter and sort rooms by name for deterministic tie-breaking
    eligible_rooms = sorted(
        [name for name, cap in rooms.items() if cap >= attendee_count]
    )

    if not eligible_rooms:
        return None, None, None

    working_start = time(cfg.WORKING_HOURS_START, 0)
    working_end = time(cfg.WORKING_HOURS_END, 0)
    slot_delta = timedelta(minutes=duration_minutes)

    # Generate all candidate slots
    candidates: list[tuple[str, datetime, datetime]] = []

    for room in eligible_rooms:
        # Get bookings for this room on this date
        room_bookings = [
            b for b in bookings_for_date
            if b["room"] == room
        ]
        room_bookings.sort(key=lambda b: b["start_time"])

        # Walk through the day to find gaps
        current = datetime.combine(target_date, working_start)
        day_ends = datetime.combine(target_date, working_end)

        for bk in room_bookings:
            bk_start = _parse_dt(bk["start_time"])
            bk_end = _parse_dt(bk["end_time"])

            # If there's a gap before this booking
            gap_end = min(bk_start, day_ends)
            if current < gap_end:
                # Fit slot in gap
                slot_start = current
                slot_end = slot_start + slot_delta
                if slot_end <= gap_end:
                    candidates.append((room, slot_start, slot_end))

            # Move current to end of this booking
            current = max(current, bk_end)

        # After all bookings
        if current < day_ends:
            slot_start = current
            slot_end = slot_start + slot_delta
            if slot_end <= day_ends:
                candidates.append((room, slot_start, slot_end))

    if not candidates:
        return None, None, None

    # Deterministic tie-breaking: earliest start, then room name alphabetically
    candidates.sort(key=lambda c: (c[1], c[0]))
    return candidates[0]


def _parse_dt(val) -> datetime:
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val))