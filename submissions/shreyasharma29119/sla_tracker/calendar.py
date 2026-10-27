"""Business-hours calendar: count / project business minutes (M1, M2).

Core operations:
  - business_minutes_between(start, end, holidays) → minutes of active time
    that fall inside business hours, excluding weekends and holidays.
  - add_business_minutes(start, minutes, holidays) → the due-by datetime
    after advancing `minutes` business minutes from `start`.

Business hours     Mon–Fri, 09:00–18:00 (configurable via SlaPolicy).
Holidays           Set of date objects — an entire business day is skipped.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, time

_BUSINESS_START = time(9, 0)
_BUSINESS_END = time(18, 0)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def _is_business_day(d: date, holidays: set[date]) -> bool:
    """True when *d* is Mon–Fri and not a holiday."""
    return d.weekday() < 5 and d not in holidays


def _minute_diff(end: datetime, start: datetime) -> float:
    """Return (end - start) in minutes as a float."""
    return (end - start).total_seconds() / 60.0


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def business_minutes_between(
    start: datetime,
    end: datetime,
    holidays: set[date],
    business_start: time = _BUSINESS_START,
    business_end: time = _BUSINESS_END,
) -> int:
    """Return the number of business minutes in [start, end).

    Weekends and holidays are excluded.  Only the portion of a business day
    that overlaps [start, end) is counted.
    """
    if start >= end:
        return 0

    total: float = 0.0
    cur_date = start.date()

    # ---- first (partial) day ------------------------------------------------
    if _is_business_day(cur_date, holidays):
        day_end = _combine(cur_date, business_end)
        if cur_date == end.date():
            eff_start = max(start, _combine(cur_date, business_start))
            eff_end = min(end, day_end)
            if eff_end > eff_start:
                total += _minute_diff(eff_end, eff_start)
            return int(total)
        eff_start = max(start, _combine(cur_date, business_start))
        if day_end > eff_start:
            total += _minute_diff(day_end, eff_start)

    cur_date += timedelta(days=1)

    # ---- full days + last day -----------------------------------------------
    while cur_date <= end.date():
        if not _is_business_day(cur_date, holidays):
            cur_date += timedelta(days=1)
            continue

        day_start = _combine(cur_date, business_start)
        day_end = _combine(cur_date, business_end)

        if cur_date == end.date():
            eff_end = min(end, day_end)
            if eff_end > day_start:
                total += _minute_diff(eff_end, day_start)
            break

        # full business day
        total += _minute_diff(day_end, day_start)
        cur_date += timedelta(days=1)

    return int(total)


def add_business_minutes(
    start: datetime,
    minutes: int,
    holidays: set[date],
    business_start: time = _BUSINESS_START,
    business_end: time = _BUSINESS_END,
) -> datetime:
    """Return the datetime `minutes` *business* minutes after *start*.

    Raises ValueError if the target falls after year 2099 (overflow guard).
    """
    if minutes < 0:
        raise ValueError("minutes must be non-negative")

    if minutes == 0:
        return start

    remaining: float = float(minutes)
    cur_date = start.date()

    # ---- first (partial) day ------------------------------------------------
    if _is_business_day(cur_date, holidays):
        day_end_dt = _combine(cur_date, business_end)
        eff_start = max(start, _combine(cur_date, business_start))
        if eff_start < day_end_dt:
            avail = _minute_diff(day_end_dt, eff_start)
            if remaining <= avail:
                return eff_start + timedelta(minutes=remaining)
            remaining -= avail

    cur_date += timedelta(days=1)

    # ---- walk forward through business days ---------------------------------
    _sentinel = date(2100, 1, 1)
    while cur_date < _sentinel:
        if not _is_business_day(cur_date, holidays):
            cur_date += timedelta(days=1)
            continue

        day_start = _combine(cur_date, business_start)
        day_end = _combine(cur_date, business_end)
        avail = _minute_diff(day_end, day_start)

        if remaining <= avail:
            return day_start + timedelta(minutes=remaining)

        remaining -= avail
        cur_date += timedelta(days=1)

    raise ValueError("Cannot compute due-by — ran past year 2099 guard")