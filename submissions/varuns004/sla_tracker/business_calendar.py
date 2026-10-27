"""Business-hours calendar arithmetic.

Works on naive local wall-clock datetimes. Both operations iterate per
calendar *day* (not per minute), so cost is O(days spanned) regardless of the
size of the SLA target.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

_ONE_DAY = timedelta(days=1)
#: Safety valve so a pathological calendar can never loop forever.
MAX_SCAN_DAYS = 366 * 100


@dataclass(frozen=True)
class BusinessCalendar:
    day_start: time
    day_end: time
    working_days: frozenset[int]  # 0 = Monday ... 6 = Sunday
    holidays: frozenset[date] = frozenset()

    def __post_init__(self) -> None:
        if self.day_start >= self.day_end:
            raise ValueError("business day start must be before business day end")
        if not self.working_days or not self.working_days <= set(range(7)):
            raise ValueError("working_days must be a non-empty subset of 0..6")

    def is_business_day(self, day: date) -> bool:
        return day.weekday() in self.working_days and day not in self.holidays

    def _window(self, day: date) -> tuple[datetime, datetime]:
        return datetime.combine(day, self.day_start), datetime.combine(day, self.day_end)

    def business_seconds(self, start: datetime, end: datetime) -> int:
        """Business seconds in the half-open interval [start, end)."""
        if end <= start:
            return 0
        total = 0
        day, last = start.date(), end.date()
        while day <= last:
            if self.is_business_day(day):
                open_, close = self._window(day)
                lo, hi = max(start, open_), min(end, close)
                if hi > lo:
                    total += int((hi - lo).total_seconds())
            day += _ONE_DAY
        return total

    def add_business_seconds(self, start: datetime, seconds: int) -> datetime:
        """Earliest instant at which ``seconds`` business seconds have elapsed.

        A deadline landing exactly on closing time is returned as closing time
        (e.g. 18:00), not as the next morning's opening time.
        """
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        if seconds == 0:
            return start
        remaining, cursor, day = seconds, start, start.date()
        for _ in range(MAX_SCAN_DAYS):
            if self.is_business_day(day):
                open_, close = self._window(day)
                lo = max(cursor, open_)
                if lo < close:
                    capacity = int((close - lo).total_seconds())
                    if remaining <= capacity:
                        return lo + timedelta(seconds=remaining)
                    remaining -= capacity
            day += _ONE_DAY
            cursor = datetime.combine(day, time.min)
        raise ValueError("due date is beyond the supported scan horizon")

