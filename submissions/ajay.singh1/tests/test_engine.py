"""Unit tests for the booking engine (pure business logic)."""
import pytest
from datetime import date, datetime, time, timedelta
from app.engine import (
    validate_booking_input,
    generate_recurrence_dates,
    build_occurrence_datetimes,
    find_earliest_slot,
    OVERLAP_ERROR, ROOM_NOT_FOUND, CAPACITY_EXCEEDED,
)
from app.rooms import load_rooms, get_rooms


class TestValidateBookingInput:
    def test_valid_booking(self, setup_test_env):
        load_rooms()
        validate_booking_input("Gamma", 4, datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 11, 0))
        # No exception

    def test_room_not_found(self, setup_test_env):
        load_rooms()
        with pytest.raises(ValueError, match=ROOM_NOT_FOUND):
            validate_booking_input("NonExistent", 4, datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 11, 0))

    def test_capacity_exceeded(self, setup_test_env):
        load_rooms()
        with pytest.raises(ValueError, match=CAPACITY_EXCEEDED):
            validate_booking_input("Alpha", 10, datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 11, 0))

    def test_capacity_at_boundary(self, setup_test_env):
        load_rooms()
        validate_booking_input("Alpha", 4, datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 11, 0))
        # No exception

    def test_start_equals_end(self, setup_test_env):
        load_rooms()
        with pytest.raises(ValueError, match="start_time must be before end_time"):
            validate_booking_input("Alpha", 2, datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 10, 0))

    def test_start_after_end(self, setup_test_env):
        load_rooms()
        with pytest.raises(ValueError, match="start_time must be before end_time"):
            validate_booking_input("Alpha", 2, datetime(2026, 12, 1, 11, 0), datetime(2026, 12, 1, 10, 0))


class TestRecurrenceDates:
    def test_single_date(self):
        """When start == end, return exactly one date."""
        dates = generate_recurrence_dates(date(2026, 12, 1), date(2026, 12, 1))
        assert dates == [date(2026, 12, 1)]

    def test_weekly_range(self):
        """Weekly recurrence: same weekday, 7 days apart."""
        dates = generate_recurrence_dates(date(2026, 12, 1), date(2026, 12, 22))  # Tue, 4 Tuesdays
        assert len(dates) == 4
        assert dates == [date(2026, 12, 1), date(2026, 12, 8), date(2026, 12, 15), date(2026, 12, 22)]

    def test_end_excluded_if_not_same_weekday(self):
        """If recurrence_end is not on the same weekday, it's not included."""
        dates = generate_recurrence_dates(date(2026, 12, 1), date(2026, 12, 10))  # Tue to Thu
        assert dates == [date(2026, 12, 1), date(2026, 12, 8)]

    def test_max_occurrences(self, monkeypatch):
        """Bounded by MAX_RECURRENCE_OCCURRENCES."""
        from app import config
        monkeypatch.setattr(config, "MAX_RECURRENCE_OCCURRENCES", 3)
        dates = generate_recurrence_dates(date(2026, 12, 1), date(2027, 12, 1))
        assert len(dates) == 3

    def test_start_after_end(self):
        dates = generate_recurrence_dates(date(2026, 12, 10), date(2026, 12, 1))
        assert dates == []

    def test_empty_dates_invalid_input(self):
        dates = generate_recurrence_dates(date(2026, 12, 10), date(2026, 12, 1))
        assert len(dates) == 0


class TestBuildOccurrenceDatetimes:
    def test_preserves_time_of_day(self):
        template_start = datetime(2026, 12, 1, 10, 30)  # Tue
        template_end = datetime(2026, 12, 1, 11, 30)
        target = date(2026, 12, 8)  # Next Tue
        st, et = build_occurrence_datetimes(template_start, template_end, target)
        assert st == datetime(2026, 12, 8, 10, 30)
        assert et == datetime(2026, 12, 8, 11, 30)

    def test_dst_transition(self):
        """During DST transitions, combining date+time is still valid."""
        template_start = datetime(2026, 3, 10, 2, 30)
        template_end = datetime(2026, 3, 10, 3, 30)
        target = date(2026, 3, 17)
        st, et = build_occurrence_datetimes(template_start, template_end, target)
        assert st.date() == target
        assert et.date() == target
        assert st.time() == time(2, 30)


class TestFindEarliestSlot:
    def test_empty_schedule_returns_9am(self, setup_test_env):
        rooms = {"Alpha": 4, "Beta": 6, "Gamma": 8}
        target = date(2026, 12, 1)
        room, start, end = find_earliest_slot(target, 60, 4, rooms, [])
        assert room == "Alpha"
        assert start == datetime(2026, 12, 1, 9, 0)
        assert end == datetime(2026, 12, 1, 10, 0)

    def test_larger_group_needs_bigger_room(self, setup_test_env):
        rooms = {"Alpha": 4, "Beta": 6, "Gamma": 8}
        target = date(2026, 12, 1)
        room, start, end = find_earliest_slot(target, 60, 5, rooms, [])
        assert room == "Beta"
        assert start == datetime(2026, 12, 1, 9, 0)

    def test_no_room_with_sufficient_capacity(self, setup_test_env):
        rooms = {"Alpha": 4, "Beta": 6}
        room, start, end = find_earliest_slot(date(2026, 12, 1), 60, 10, rooms, [])
        assert room is None

    def test_skips_conflicting_bookings(self, setup_test_env):
        rooms = {"Alpha": 4, "Beta": 6}
        bookings = [
            {"room": "Alpha", "start_time": "2026-12-01T09:00:00", "end_time": "2026-12-01T10:00:00"},
        ]
        room, start, end = find_earliest_slot(date(2026, 12, 1), 60, 4, rooms, bookings)
        # Alpha is booked 9-10, earliest for Alpha is 10:00
        # But Beta is free at 9:00 — tiebreak by start time, both at 9:00, then alphabetically: Alpha < Beta but Alpha is booked
        # Actually: Alpha at 10:00 vs Beta at 9:00 — Beta wins (earlier start)
        assert room == "Beta"
        assert start == datetime(2026, 12, 1, 9, 0)

    def test_fully_booked_day(self, setup_test_env):
        rooms = {"Alpha": 4}
        bookings = [
            {"room": "Alpha", "start_time": "2026-12-01T09:00:00", "end_time": "2026-12-01T18:00:00"},
        ]
        room, start, end = find_earliest_slot(date(2026, 12, 1), 30, 2, rooms, bookings)
        assert room is None

    def test_duration_exceeds_working_hours(self, setup_test_env):
        rooms = {"Alpha": 4}
        room, start, end = find_earliest_slot(date(2026, 12, 1), 600, 2, rooms, [])
        assert room is None  # 600 minutes > 540 (9 hours)

    def test_back_to_back_allowed(self, setup_test_env):
        """Back-to-back: booking 9–10, slot at 10 is valid."""
        rooms = {"Alpha": 4}
        bookings = [
            {"room": "Alpha", "start_time": "2026-12-01T09:00:00", "end_time": "2026-12-01T10:00:00"},
        ]
        room, start, end = find_earliest_slot(date(2026, 12, 1), 60, 2, rooms, bookings)
        assert room == "Alpha"
        assert start == datetime(2026, 12, 1, 10, 0)
        assert end == datetime(2026, 12, 1, 11, 0)

    def test_deterministic_tie_breaking(self, setup_test_env):
        """Same start time: choose alphabetically first room."""
        rooms = {"Beta": 6, "Alpha": 4}
        target = date(2026, 12, 1)
        room, start, end = find_earliest_slot(target, 30, 2, rooms, [])
        assert room == "Alpha"  # Alphabetical
        assert start == datetime(2026, 12, 1, 9, 0)