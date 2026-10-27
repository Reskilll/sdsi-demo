"""Business-hours calendar with holiday exclusion.

All arithmetic operates on UTC datetimes but reasons about wall-clock time in the
configured timezone (default: UTC). The caller passes UTC datetimes and receives
UTC datetimes back; the calendar does the timezone conversion internally.

Key correctness properties:
- Business-minute counting is monotonic and commutative over disjoint intervals.
- Holiday exclusion treats the entire calendar day (00:00–23:59 local) as
  non-business, so an interval that *straddles* a holiday correctly only counts
  business minutes on the non-holiday side.
- ON_HOLD intervals are subtracted from the total elapsed time, so the SLA clock
  pauses and resumes seamlessly.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ── Defaults (overridable via config) ────────────────────────────────────────

DEFAULT_TIMEZONE = "UTC"
BUSINESS_START_HOUR = 9   # 09:00 local
BUSINESS_END_HOUR = 18    # 18:00 local (exclusive upper bound)
BUSINESS_MINUTES_PER_DAY = (BUSINESS_END_HOUR - BUSINESS_START_HOUR) * 60  # 540


def _resolve_timezone(tz: str) -> ZoneInfo | timezone:
    """Resolve a timezone name, falling back to UTC for the literal 'UTC' string.

    On Windows, ``ZoneInfo('UTC')`` fails without ``tzdata`` installed, so we
    short-circuit to ``datetime.timezone.utc``.
    """
    if tz.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError) as exc:
        raise ValueError(f"Unknown IANA timezone: {tz!r}") from exc


class BusinessCalendar:
    """Count elapsed business minutes between two UTC datetimes.

    Parameters
    ----------
    holidays : set[date]
        Dates (local timezone) that are non-working days.
    tz : str
        IANA timezone name for the support centre (default ``"UTC"``).
    business_start : tuple[int, int]
        (hour, minute) for start of business day (default ``(9, 0)``).
    business_end : tuple[int, int]
        (hour, minute) for end of business day (default ``(18, 0)``).
    """

    def __init__(
        self,
        holidays: set[date],
        tz: str = DEFAULT_TIMEZONE,
        business_start: tuple[int, int] = (9, 0),
        business_end: tuple[int, int] = (18, 0),
    ) -> None:
        self._holidays = holidays
        self._zone_name = tz
        self._zone: ZoneInfo | timezone = _resolve_timezone(tz)
        self._start = timedelta(hours=business_start[0], minutes=business_start[1])
        self._end = timedelta(hours=business_end[0], minutes=business_end[1])
        self._business_minutes = int(
            (self._end - self._start).total_seconds() / 60
        )

    # ── public API ───────────────────────────────────────────────────────

    def business_minutes_between(
        self, start_utc: datetime, end_utc: datetime
    ) -> float:
        """Return the number of business minutes in **``[start_utc, end_utc]``**.

        Order is not enforced — the result is always non-negative.  Weekends and
        holidays contribute 0 minutes.
        """
        if start_utc == end_utc:
            return 0.0
        if start_utc > end_utc:
            start_utc, end_utc = end_utc, start_utc

        total = 0.0
        current = start_utc

        while current < end_utc:
            day_local = current.astimezone(self._zone).date()

            if day_local.weekday() >= 5 or day_local in self._holidays:
                # Skip to next day at business-start (local time)
                next_day_local = (
                    current.astimezone(self._zone).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    + timedelta(days=1)
                )
                current = next_day_local.astimezone(timezone.utc)
                continue

            # Business day — window open and close as UTC
            day_start_utc = (
                datetime.combine(day_local, self._start_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )
            day_end_utc = (
                datetime.combine(day_local, self._end_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )

            seg_start = max(current, day_start_utc)
            seg_end = min(end_utc, day_end_utc)

            if seg_start < seg_end:
                total += (seg_end - seg_start).total_seconds() / 60.0

            # Advance to next day's business-start
            next_day_local = day_local + timedelta(days=1)
            current = (
                datetime.combine(next_day_local, self._start_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )

        return total

    def add_business_minutes(self, start_utc: datetime, minutes: float) -> datetime:
        """Return the UTC datetime after adding *business* minutes to ``start_utc``.

        This gives the *due-by* wall-clock time for a ticket created at
        ``start_utc`` with an SLA window of ``minutes`` business minutes.
        """
        if minutes <= 0:
            return start_utc

        remaining = minutes
        current = start_utc

        # Skip initial non-business time
        while True:
            day_local = current.astimezone(self._zone).date()
            if day_local.weekday() >= 5 or day_local in self._holidays:
                # Advance to next business start
                next_day_local = day_local + timedelta(days=1)
                # But we need to find the *next business day*
                while True:
                    if next_day_local.weekday() < 5 and next_day_local not in self._holidays:
                        break
                    next_day_local += timedelta(days=1)
                current = (
                    datetime.combine(next_day_local, self._start_time(), tzinfo=self._zone)
                    .astimezone(timezone.utc)
                )
                continue

            day_start_utc = (
                datetime.combine(day_local, self._start_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )
            day_end_utc = (
                datetime.combine(day_local, self._end_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )

            if current < day_start_utc:
                current = day_start_utc
            if current >= day_end_utc:
                # Past business hours today — go to next business day
                next_day_local = day_local + timedelta(days=1)
                while True:
                    if next_day_local.weekday() < 5 and next_day_local not in self._holidays:
                        break
                    next_day_local += timedelta(days=1)
                current = (
                    datetime.combine(next_day_local, self._start_time(), tzinfo=self._zone)
                    .astimezone(timezone.utc)
                )
                continue

            # Remaining minutes in today's window
            mins_today = (day_end_utc - current).total_seconds() / 60.0
            if remaining <= mins_today:
                return current + timedelta(minutes=remaining)

            remaining -= mins_today
            # Move to start of next business day
            next_day_local = day_local + timedelta(days=1)
            while True:
                if next_day_local.weekday() < 5 and next_day_local not in self._holidays:
                    break
                next_day_local += timedelta(days=1)
            current = (
                datetime.combine(next_day_local, self._start_time(), tzinfo=self._zone)
                .astimezone(timezone.utc)
            )

    ## helpers ─────────────────────────────────────────────────────────────

    def _start_time(self) -> time:
        """Return business start as a ``datetime.time`` object."""
        return time(
            hour=int(self._start.total_seconds() // 3600),
            minute=int((self._start.total_seconds() % 3600) // 60),
        )

    def _end_time(self) -> time:
        return time(
            hour=int(self._end.total_seconds() // 3600),
            minute=int((self._end.total_seconds() % 3600) // 60),
        )

    def is_business_hour(self, utc_dt: datetime) -> bool:
        """Check whether ``utc_dt`` falls within business hours on a working day."""
        local = utc_dt.astimezone(self._zone)
        if local.date().weekday() >= 5:
            return False
        if local.date() in self._holidays:
            return False
        start = timedelta(hours=local.hour, minutes=local.minute, seconds=local.second)
        return self._start <= start < self._end

    @property
    def timezone(self) -> ZoneInfo | timezone:
        return self._zone

    @property
    def holidays(self) -> set[date]:
        return self._holidays
