"""Tests for the business-hours calendar."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from sla_tracker.business_calendar import BusinessCalendar

UTC = timezone.utc


@pytest.fixture
def no_holidays() -> BusinessCalendar:
    return BusinessCalendar(holidays=set(), tz="UTC")


@pytest.fixture
def with_holiday() -> BusinessCalendar:
    # Oct 27, 2026 is a Tuesday — make it a holiday
    return BusinessCalendar(holidays={date(2026, 10, 27)}, tz="UTC")


class TestBusinessMinutesBetween:
    """Test business_minutes_between correctness."""

    def test_zero_interval(self, no_holidays: BusinessCalendar) -> None:
        now = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        assert no_holidays.business_minutes_between(now, now) == 0.0

    def test_full_business_day(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)   # Monday
        end = datetime(2026, 10, 26, 18, 0, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 540.0

    def test_half_day(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
        end = datetime(2026, 10, 26, 13, 30, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 270.0

    def test_before_business(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 6, 0, tzinfo=UTC)
        end = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 180.0

    def test_after_business(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        end = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 360.0

    def test_overnight(self, no_holidays: BusinessCalendar) -> None:
        # Friday 17:00 → Monday 10:00
        start = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)
        end = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)
        # Friday: 17:00–18:00 = 60; Monday: 09:00–10:00 = 60 → 120
        assert no_holidays.business_minutes_between(start, end) == 120.0

    def test_weekend_excluded(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)  # Saturday
        end = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)    # Sunday
        assert no_holidays.business_minutes_between(start, end) == 0.0

    def test_holiday_excluded(self, with_holiday: BusinessCalendar) -> None:
        # Oct 27 is a holiday — full business day should yield 0
        start = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
        end = datetime(2026, 10, 27, 18, 0, tzinfo=UTC)
        assert with_holiday.business_minutes_between(start, end) == 0.0

    def test_holiday_straddle(self, with_holiday: BusinessCalendar) -> None:
        # Oct 26 (Mon) 10:00 → Oct 28 (Wed) 12:00, Oct 27 is holiday
        start = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)
        end = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
        # Mon: 10:00-18:00 = 480; Tue (holiday): 0; Wed: 09:00-12:00 = 180 → 660
        assert with_holiday.business_minutes_between(start, end) == 660.0

    def test_reversed_params(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 18, 0, tzinfo=UTC)
        end = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 540.0

    def test_partial_minutes(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 9, 15, 30, tzinfo=UTC)
        end = datetime(2026, 10, 26, 9, 45, 30, tzinfo=UTC)
        assert no_holidays.business_minutes_between(start, end) == 30.0


class TestAddBusinessMinutes:
    """Test add_business_minutes correctness."""

    def test_add_within_day(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
        result = no_holidays.add_business_minutes(start, 120)
        assert result == datetime(2026, 10, 26, 11, 0, tzinfo=UTC)

    def test_add_crosses_day_boundary(self, no_holidays: BusinessCalendar) -> None:
        # 540 min = 9h exactly fills one business day (09:00→18:00 same day).
        # 541 min crosses: Mon 09:00 + 540m = Mon 18:00, remaining 1m → Tue 09:01.
        start = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
        result = no_holidays.add_business_minutes(start, 541)
        assert result == datetime(2026, 10, 27, 9, 1, tzinfo=UTC)

    def test_add_spans_weekend(self, no_holidays: BusinessCalendar) -> None:
        # Friday at 17:00 + 120 min = Monday at 11:00
        start = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)
        result = no_holidays.add_business_minutes(start, 120)
        # Fri: 17:00–18:00 = 60; Mon: 09:00–10:00 = 60 → 10:00
        assert result == datetime(2026, 10, 26, 10, 0, tzinfo=UTC)

    def test_add_zero(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        assert no_holidays.add_business_minutes(start, 0) == start

    def test_add_negative(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
        assert no_holidays.add_business_minutes(start, -5) == start

    def test_start_on_weekend(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)  # Saturday
        result = no_holidays.add_business_minutes(start, 60)
        assert result == datetime(2026, 10, 26, 10, 0, tzinfo=UTC)  # Mon 10:00

    def test_start_on_holiday(self, with_holiday: BusinessCalendar) -> None:
        start = datetime(2026, 10, 27, 10, 0, tzinfo=UTC)  # Holiday
        result = with_holiday.add_business_minutes(start, 60)
        assert result == datetime(2026, 10, 28, 10, 0, tzinfo=UTC)

    def test_add_spans_holiday(self, with_holiday: BusinessCalendar) -> None:
        # Oct 26 17:00 + 2 business hours (120 min)
        start = datetime(2026, 10, 26, 17, 0, tzinfo=UTC)
        result = with_holiday.add_business_minutes(start, 120)
        # Mon: 17:00–18:00 = 60; Tue (holiday) skipped; Wed: 09:00–10:00 = 60
        assert result == datetime(2026, 10, 28, 10, 0, tzinfo=UTC)

    def test_start_after_business(self, no_holidays: BusinessCalendar) -> None:
        start = datetime(2026, 10, 26, 19, 0, tzinfo=UTC)  # After 18:00
        result = no_holidays.add_business_minutes(start, 60)
        assert result == datetime(2026, 10, 27, 10, 0, tzinfo=UTC)


class TestIsBusinessHour:
    """Test is_business_hour."""

    def test_during_business(self, no_holidays: BusinessCalendar) -> None:
        assert no_holidays.is_business_hour(datetime(2026, 10, 26, 10, 0, tzinfo=UTC))

    def test_before_business(self, no_holidays: BusinessCalendar) -> None:
        assert not no_holidays.is_business_hour(datetime(2026, 10, 26, 8, 0, tzinfo=UTC))

    def test_after_business(self, no_holidays: BusinessCalendar) -> None:
        assert not no_holidays.is_business_hour(datetime(2026, 10, 26, 18, 0, tzinfo=UTC))

    def test_weekend(self, no_holidays: BusinessCalendar) -> None:
        assert not no_holidays.is_business_hour(datetime(2026, 10, 24, 10, 0, tzinfo=UTC))

    def test_holiday(self, with_holiday: BusinessCalendar) -> None:
        assert not with_holiday.is_business_hour(datetime(2026, 10, 27, 10, 0, tzinfo=UTC))
