"""Calendar arithmetic & boundary tests."""

import unittest
from datetime import datetime, timezone, timedelta

from sla_tracker.calendar import (
    HolidayCalendar,
    is_business_day,
    business_day_start,
    business_day_end,
    next_business_day,
    prev_business_day,
    clamp_to_business_hours,
    business_minutes_between,
    project_due_by,
    BUSINESS_MINUTES_PER_DAY,
)


class TestBusinessDayDetection(unittest.TestCase):
    def test_monday_is_business_day(self):
        dt = datetime(2026, 10, 26)  # Monday
        self.assertTrue(is_business_day(dt))

    def test_saturday_not_business_day(self):
        dt = datetime(2026, 10, 31)  # Saturday
        self.assertFalse(is_business_day(dt))

    def test_sunday_not_business_day(self):
        dt = datetime(2026, 10, 25)  # Sunday
        self.assertFalse(is_business_day(dt))


class TestBusinessDayBoundaries(unittest.TestCase):
    def test_start_monday(self):
        dt = datetime(2026, 10, 26, 14, 30)
        result = business_day_start(dt)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 0)

    def test_start_saturday_returns_monday(self):
        dt = datetime(2026, 10, 31, 14, 30)  # Saturday
        result = business_day_start(dt)
        self.assertEqual(result.weekday(), 0)  # Monday
        self.assertEqual(result.hour, 9)

    def test_next_business_day_friday_to_monday(self):
        dt = datetime(2026, 10, 30, 14, 0)  # Friday
        result = next_business_day(dt)
        self.assertEqual(result.weekday(), 0)  # Monday

    def test_prev_business_day_monday_to_friday(self):
        dt = datetime(2026, 10, 26, 14, 0)  # Monday
        result = prev_business_day(dt)
        self.assertEqual(result.weekday(), 4)  # Friday


class TestClampToBusinessHours(unittest.TestCase):
    def test_before_9am(self):
        dt = datetime(2026, 10, 26, 6, 30)  # Monday 6:30
        result = clamp_to_business_hours(dt)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 0)

    def test_after_6pm(self):
        dt = datetime(2026, 10, 26, 20, 30)  # Monday 20:30
        result = clamp_to_business_hours(dt)
        self.assertEqual(result.hour, 18)
        self.assertEqual(result.minute, 0)

    def test_during_business(self):
        dt = datetime(2026, 10, 26, 14, 30)
        result = clamp_to_business_hours(dt)
        self.assertEqual(result, dt)

    def test_saturday_clamp(self):
        dt = datetime(2026, 10, 31, 14, 30)  # Saturday
        result = clamp_to_business_hours(dt)
        self.assertEqual(result.weekday(), 4)  # Friday
        self.assertEqual(result.hour, 18)


class TestHolidayCalendar(unittest.TestCase):
    def setUp(self):
        self.holidays = HolidayCalendar(["2026-01-01", "2026-12-25"])

    def test_known_holiday(self):
        self.assertTrue(self.holidays.is_holiday(datetime(2026, 1, 1)))

    def test_regular_day(self):
        self.assertFalse(self.holidays.is_holiday(datetime(2026, 3, 15)))

    def test_date_string_contains(self):
        self.assertIn("2026-01-01", self.holidays)

    def test_empty_holidays(self):
        h = HolidayCalendar()
        self.assertFalse(h.is_holiday(datetime(2026, 1, 1)))


class TestBusinessMinutesBetween(unittest.TestCase):
    def setUp(self):
        self.holidays = HolidayCalendar(["2026-01-01"])

    def test_same_business_day(self):
        start = datetime(2026, 10, 26, 9, 0)  # Monday
        end = datetime(2026, 10, 26, 12, 0)
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 180)

    def test_full_business_day(self):
        start = datetime(2026, 10, 26, 9, 0)
        end = datetime(2026, 10, 26, 18, 0)
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 540)

    def test_zero_if_start_after_end(self):
        start = datetime(2026, 10, 26, 14, 0)
        end = datetime(2026, 10, 26, 10, 0)
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 0)

    def test_ec1_created_outside_business_hours(self):
        """Sunday 14:00 to Monday 11:00 = 120 business minutes."""
        start = datetime(2026, 10, 25, 14, 0)  # Sunday
        end = datetime(2026, 10, 26, 11, 0)    # Monday
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 120)  # Mon 09:00-11:00

    def test_ec2_resolved_outside_business_hours(self):
        """Monday 14:00 to Saturday 12:00 = only Monday-Friday business hours counted."""
        start = datetime(2026, 10, 26, 14, 0)  # Monday
        end = datetime(2026, 10, 31, 12, 0)    # Saturday
        mins = business_minutes_between(start, end)
        # Mon 14:00-18:00 = 240, Tue-Fri = 4*540 = 2160, Sat = 0
        self.assertEqual(mins, 240 + 2160)

    def test_ec8_multi_day_with_holiday(self):
        """Monday-Tuesday with Tuesday as holiday = 1 business day."""
        h = HolidayCalendar(["2026-10-27"])
        start = datetime(2026, 10, 26, 9, 0)   # Monday
        end = datetime(2026, 10, 28, 9, 0)     # Wednesday
        mins = business_minutes_between(start, end, h)
        self.assertEqual(mins, 540)  # Monday only (Tuesday skipped)

    def test_after_hours_start(self):
        start = datetime(2026, 10, 26, 20, 0)  # Monday evening
        end = datetime(2026, 10, 27, 12, 0)    # Tuesday noon
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 180)  # Tue 09:00-12:00

    def test_weekend_to_weekend(self):
        start = datetime(2026, 10, 24, 14, 0)  # Saturday
        end = datetime(2026, 10, 25, 14, 0)    # Sunday
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 0)

    def test_multi_week_span(self):
        start = datetime(2026, 10, 26, 9, 0)   # Monday
        end = datetime(2026, 11, 2, 18, 0)     # Next Monday
        mins = business_minutes_between(start, end)
        # 6 business days (Mon-Fri + Mon) = 6 * 540
        self.assertEqual(mins, 6 * 540)

    def test_timezone_aware_inputs(self):
        tz = timezone(timedelta(hours=5, minutes=30))
        start = datetime(2026, 10, 26, 9, 0, tzinfo=tz)
        end = datetime(2026, 10, 26, 12, 0, tzinfo=tz)
        mins = business_minutes_between(start, end)
        self.assertEqual(mins, 180)


class TestProjectDueBy(unittest.TestCase):
    def setUp(self):
        self.holidays = HolidayCalendar()

    def test_same_day_projection(self):
        start = datetime(2026, 10, 26, 9, 0)  # Monday
        due = project_due_by(start, 120, self.holidays)
        self.assertEqual(due, datetime(2026, 10, 26, 11, 0))

    def test_cross_day_projection(self):
        start = datetime(2026, 10, 26, 17, 0)  # Monday, 1 hour left
        due = project_due_by(start, 120, self.holidays)
        # 1h Mon (17:00-18:00) + 1h Tue (09:00-10:00)
        self.assertEqual(due, datetime(2026, 10, 27, 10, 0))

    def test_weekend_skipping(self):
        start = datetime(2026, 10, 30, 17, 0)  # Friday
        due = project_due_by(start, 120, self.holidays)
        # 1h Friday (17:00-18:00) + 1h Monday (09:00-10:00)
        self.assertEqual(due.weekday(), 0)  # Monday
        self.assertEqual(due.hour, 10)

    def test_p4_target_72h(self):
        start = datetime(2026, 10, 26, 9, 0)  # Monday
        due = project_due_by(start, 4320, self.holidays)  # P4 = 72h = 8 business days
        # 8 full business days from Monday 09:00 = Wednesday 18:00 (exactly 8×540 min)
        self.assertEqual(due.weekday(), 2)  # Wednesday
        self.assertEqual(due.hour, 18)

    def test_holiday_skip(self):
        h = HolidayCalendar(["2026-10-27"])  # Tuesday is holiday
        start = datetime(2026, 10, 26, 17, 0)  # Monday
        due = project_due_by(start, 540, h)  # Full day
        # 1h Monday + 9h Wednesday = 1h Mon + full Wed = Wed 17:00? No.
        # 1h Monday (17-18) = 60 min on Monday. 480 remaining for Wednesday.
        self.assertEqual(due.weekday(), 2)  # Wednesday


class TestBusinessMinutesPerDay(unittest.TestCase):
    def test_correct_minutes(self):
        self.assertEqual(BUSINESS_MINUTES_PER_DAY, 540)


if __name__ == "__main__":
    unittest.main()