import time as wallclock
import unittest
from datetime import date, time, timedelta

from sla_tracker.business_calendar import BusinessCalendar

from .helpers import calendar, dt


class BusinessSecondsTest(unittest.TestCase):
    def setUp(self):
        self.cal = calendar()

    def mins(self, a, b, cal=None):
        return (cal or self.cal).business_seconds(a, b) // 60

    def test_same_day(self):
        self.assertEqual(self.mins(dt(5, 10), dt(5, 12, 30)), 150)

    def test_overnight(self):
        self.assertEqual(self.mins(dt(5, 17), dt(6, 10)), 120)

    def test_spans_weekend(self):
        self.assertEqual(self.mins(dt(9, 17), dt(12, 10)), 120)

    def test_start_before_and_end_after_hours(self):
        self.assertEqual(self.mins(dt(5, 7), dt(5, 20)), 540)

    def test_entirely_on_weekend(self):
        self.assertEqual(self.mins(dt(10, 9), dt(11, 18)), 0)

    def test_entirely_outside_hours(self):
        self.assertEqual(self.mins(dt(5, 18), dt(6, 9)), 0)

    def test_holiday_excluded(self):
        cal = calendar(date(2026, 10, 6))
        self.assertEqual(self.mins(dt(5, 17), dt(7, 10), cal), 120)

    def test_reversed_or_empty_interval_is_zero(self):
        self.assertEqual(self.mins(dt(5, 12), dt(5, 10)), 0)
        self.assertEqual(self.mins(dt(5, 12), dt(5, 12)), 0)

    def test_seconds_precision(self):
        self.assertEqual(self.cal.business_seconds(dt(5, 10), dt(5, 10) + timedelta(seconds=30)), 30)


class AddBusinessSecondsTest(unittest.TestCase):
    def setUp(self):
        self.cal = calendar()

    def add(self, start, minutes, cal=None):
        return (cal or self.cal).add_business_seconds(start, minutes * 60)

    def test_rolls_to_next_day(self):
        self.assertEqual(self.add(dt(5, 17), 240), dt(6, 12))

    def test_lands_exactly_on_close(self):
        self.assertEqual(self.add(dt(5, 14), 240), dt(5, 18))

    def test_from_weekend(self):
        self.assertEqual(self.add(dt(10, 12), 60), dt(12, 10))

    def test_from_after_hours(self):
        self.assertEqual(self.add(dt(5, 19), 30), dt(6, 9, 30))

    def test_skips_holiday_after_weekend(self):
        cal = calendar(date(2026, 10, 12))
        self.assertEqual(self.add(dt(9, 17, 30), 60, cal), dt(13, 9, 30))

    def test_zero_returns_start(self):
        self.assertEqual(self.add(dt(10, 12), 0), dt(10, 12))

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            self.cal.add_business_seconds(dt(5, 10), -1)

    def test_round_trip_property(self):
        for start in (dt(5, 8), dt(5, 13, 17), dt(9, 17, 59), dt(10, 3)):
            for minutes in (1, 59, 540, 541, 4320):
                end = self.add(start, minutes)
                self.assertEqual(self.cal.business_seconds(start, end), minutes * 60)


class CalendarValidationTest(unittest.TestCase):
    def test_start_after_end_rejected(self):
        with self.assertRaises(ValueError):
            BusinessCalendar(time(18), time(9), frozenset({0}))

    def test_no_working_days_rejected(self):
        with self.assertRaises(ValueError):
            BusinessCalendar(time(9), time(18), frozenset())

    def test_invalid_weekday_rejected(self):
        with self.assertRaises(ValueError):
            BusinessCalendar(time(9), time(18), frozenset({7}))


class PerformanceTest(unittest.TestCase):
    def test_multi_year_span_is_fast(self):
        cal = calendar()
        t0 = wallclock.perf_counter()
        for _ in range(100):
            cal.business_seconds(dt(1, 9, month=1), dt(1, 9, month=1) + timedelta(days=365 * 5))
        self.assertLess(wallclock.perf_counter() - t0, 2.0)


if __name__ == "__main__":
    unittest.main()

