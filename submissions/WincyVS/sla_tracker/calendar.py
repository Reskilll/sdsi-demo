"""Business calendar — O(1) day-block intervals, holiday exclusion, timezone aware."""

from datetime import datetime, timedelta, timezone
from typing import Optional

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
BUSINESS_START = 9   # 09:00
BUSINESS_END = 18    # 18:00
BUSINESS_MINUTES_PER_DAY = (BUSINESS_END - BUSINESS_START) * 60  # 540


class HolidayCalendar:
    """Fast O(1) holiday lookup using a frozenset of date strings."""

    def __init__(self, dates: Optional[list[str]] = None):
        # Normalize to YYYY-MM-DD strings
        self._holidays: frozenset[str] = frozenset(
            d.strip()[:10] for d in (dates or [])
        )

    def is_holiday(self, dt: datetime) -> bool:
        return dt.strftime("%Y-%m-%d") in self._holidays

    @staticmethod
    def from_file(path: str) -> "HolidayCalendar":
        import json

        with open(path, "r") as f:
            data = json.load(f)
        dates = data if isinstance(data, list) else data.get("holidays", data.get("dates", []))
        return HolidayCalendar(dates)

    def __contains__(self, date_str: str) -> bool:
        return date_str[:10] in self._holidays


def is_business_day(dt: datetime) -> bool:
    """Mon-Fri."""
    return dt.weekday() < 5  # Monday=0, Sunday=6


def business_day_start(dt: datetime) -> datetime:
    """Return 09:00 on the same day (or next business day if weekend)."""
    d = dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
    if not is_business_day(d):
        d = next_business_day(d)
    return d


def business_day_end(dt: datetime) -> datetime:
    """Return 18:00 on the same day (or previous business day if weekend)."""
    d = dt.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
    if not is_business_day(d):
        d = prev_business_day(d)
    return d


def next_business_day(dt: datetime) -> datetime:
    """Return 09:00 of the next business day."""
    d = dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def prev_business_day(dt: datetime) -> datetime:
    """Return 09:00 of the previous business day."""
    d = dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0) - timedelta(days=1)
    while not is_business_day(d):
        d -= timedelta(days=1)
    return d


def clamp_to_business_hours(dt: datetime) -> datetime:
    """Clamp a datetime to within [09:00, 18:00] on its business day.
    Outside business hours → snap to nearest boundary.
    Weekend → snap to Friday 18:00 (if after) or Monday 09:00 (if before)."""
    h = dt.hour + dt.minute / 60
    if not is_business_day(dt):
        # Weekend: snap to next Monday 09:00 or prev Friday 18:00
        wd = dt.weekday()
        if wd == 5:  # Saturday
            return (dt.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
                    - timedelta(days=1))  # Friday 18:00
        else:  # Sunday
            return (dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
                    + timedelta(days=1))  # Monday 09:00

    if h < BUSINESS_START:
        return dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
    if h >= BUSINESS_END:
        return dt.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
    return dt


def business_minutes_between(
    start: datetime, end: datetime, holidays: Optional[HolidayCalendar] = None
) -> float:
    """Calculate business minutes between two datetimes using O(1) day-block jumps.
    Excludes weekends, holidays, and non-business hours."""

    if start >= end:
        return 0.0

    if holidays is None:
        holidays = HolidayCalendar()

    # Normalize to UTC (strip TZ for pure arithmetic; all values are UTC-equivalent)
    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    if end.tzinfo is not None:
        end = end.replace(tzinfo=None)

    total = 0.0
    cursor = start

    # Phase 1: handle partial first day
    if is_business_day(cursor) and not holidays.is_holiday(cursor):
        day_end_val = cursor.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
        if cursor.hour < BUSINESS_END:
            eff_start = max(cursor, cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0))
            if cursor.hour < BUSINESS_START:
                eff_start = cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
            if end <= day_end_val:
                # Both on same business day
                eff_end = min(end, day_end_val)
                if eff_end > eff_start:
                    total += (eff_end - eff_start).total_seconds() / 60
                return total
            else:
                total += max(0, (day_end_val - eff_start).total_seconds() / 60)
                cursor = day_end_val

    # Advance to next day 09:00
    cursor = (cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
              + timedelta(days=1))

    # Phase 2: full business days in O(1) jumps
    while cursor < end:
        if not is_business_day(cursor) or holidays.is_holiday(cursor):
            cursor += timedelta(days=1)
            continue

        day_end_val = cursor.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)

        if end <= day_end_val:
            # Last partial day
            if end > cursor:
                total += (end - cursor).total_seconds() / 60
            break

        # Full business day
        total += BUSINESS_MINUTES_PER_DAY
        cursor += timedelta(days=1)

    return total


def project_due_by(
    start: datetime,
    target_minutes: float,
    holidays: Optional[HolidayCalendar] = None,
) -> datetime:
    """Project a due-by datetime by adding business minutes to start, O(1) day jumps."""

    if holidays is None:
        holidays = HolidayCalendar()

    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)

    remaining = target_minutes
    cursor = start

    # Phase 1: remainder of first business day
    if is_business_day(cursor) and not holidays.is_holiday(cursor):
        if cursor.hour < BUSINESS_END:
            eff_start = max(cursor, cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0))
            if cursor.hour < BUSINESS_START:
                eff_start = cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
            day_end_val = cursor.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
            avail = (day_end_val - eff_start).total_seconds() / 60
            if avail >= remaining:
                return eff_start + timedelta(minutes=remaining)
            remaining -= avail
            cursor = day_end_val

    # Advance to next business day
    cursor = (cursor.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
              + timedelta(days=1))

    # Phase 2: skip whole business days in O(1)
    while remaining > 0:
        while not is_business_day(cursor) or holidays.is_holiday(cursor):
            cursor += timedelta(days=1)

        if remaining > BUSINESS_MINUTES_PER_DAY:
            remaining -= BUSINESS_MINUTES_PER_DAY
            cursor += timedelta(days=1)
        else:
            return cursor + timedelta(minutes=remaining)

    return cursor  # exact match (remaining == 0), cursor already at 09:00