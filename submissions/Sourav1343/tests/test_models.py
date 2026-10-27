"""Unit tests for models and schema validation (M1 edge cases)."""

from __future__ import annotations

import pytest
from engine.models import Booking, BookingRequest, BookingResult, Conflict, Room, Slot
from engine.validator import (
    check_capacity,
    overlaps,
    validate_booking_request,
    to_booking,
)


# ---------------------------------------------------------------------------
# Room / models smoke tests
# ---------------------------------------------------------------------------

def test_room_immutable():
    r = Room(id="r1", name="Alpha", capacity=4)
    with pytest.raises(Exception):
        r.capacity = 10  # type: ignore[misc]


def test_booking_duration():
    from datetime import datetime
    b = Booking(
        id="b1", room_id="r1", organiser="alice",
        start_time=datetime(2026, 1, 1, 10, 0),
        end_time=datetime(2026, 1, 1, 11, 30),
        attendees=["bob"],
    )
    assert b.duration_minutes() == 90
    assert b.attendee_count() == 1
    assert not b.is_recurring()


def test_booking_recurring_flag():
    from datetime import datetime, date
    b = Booking(
        id="b1", room_id="r1", organiser="alice",
        start_time=datetime(2026, 1, 1, 10, 0),
        end_time=datetime(2026, 1, 1, 11, 0),
        attendees=["bob"],
        recurrence_weekly_until=date(2026, 12, 31),
    )
    assert b.is_recurring()


# ---------------------------------------------------------------------------
# Overlap rules (M2)
# ---------------------------------------------------------------------------

class TestOverlap:
    """Half-open interval overlap: a_start < b_end AND b_start < a_end."""

    D1 = "2026-10-27T09:00"
    D2 = "2026-10-27T09:30"
    D3 = "2026-10-27T10:00"
    D4 = "2026-10-27T10:30"
    D5 = "2026-10-27T11:00"

    def _dt(self, s):
        from datetime import datetime
        return datetime.fromisoformat(s)

    def test_back_to_back_not_overlap(self):
        a = self._dt(self.D1); b = self._dt(self.D2)
        c = self._dt(self.D2); d = self._dt(self.D3)
        assert not overlaps(a, b, c, d)

    def test_overlap_b_starts_before_a_ends(self):
        a = self._dt(self.D1); b = self._dt(self.D3)  # 09:00–10:00
        c = self._dt(self.D2); d = self._dt(self.D4)  # 09:30–10:30
        assert overlaps(a, b, c, d)

    def test_overlap_a_contains_b(self):
        a = self._dt(self.D1); b = self._dt(self.D5)  # 09:00–11:00
        c = self._dt(self.D2); d = self._dt(self.D4)  # 09:30–10:30
        assert overlaps(a, b, c, d)

    def test_overlap_b_contains_a(self):
        a = self._dt(self.D2); b = self._dt(self.D4)  # 09:30–10:30
        c = self._dt(self.D1); d = self._dt(self.D5)  # 09:00–11:00
        assert overlaps(a, b, c, d)

    def test_overlap_same_interval(self):
        a = self._dt(self.D1); b = self._dt(self.D3)
        assert overlaps(a, b, a, b)

    def test_no_overlap_separate(self):
        a = self._dt(self.D1); b = self._dt(self.D2)   # 09:00–09:30
        c = self._dt(self.D3); d = self._dt(self.D4)   # 10:00–10:30
        assert not overlaps(a, b, c, d)

    def test_no_overlap_touching_exact(self):
        a = self._dt(self.D1); b = self._dt(self.D2)   # 09:00–09:30
        c = self._dt(self.D2); d = self._dt(self.D3)   # 09:30–10:00
        assert not overlaps(a, b, c, d)


# ---------------------------------------------------------------------------
# Capacity check
# ---------------------------------------------------------------------------

def test_capacity_under():
    assert check_capacity(3, Room("r", "x", 5)) is None


def test_capacity_exact():
    assert check_capacity(5, Room("r", "x", 5)) is None


def test_capacity_over():
    err = check_capacity(6, Room("r", "x", 5))
    assert err is not None
    assert "capacity" in err


# ---------------------------------------------------------------------------
# Booking validation
# ---------------------------------------------------------------------------

ROOMS = {"r1": Room("r1", "Alpha", 4)}
EXISTING = set()


def make_req(**overrides):
    defaults = {
        "id": "b1",
        "room_id": "r1",
        "organiser": "alice",
        "start_time": "2026-10-27T09:00",
        "end_time": "2026-10-27T10:00",
        "attendees": ["bob"],
        "recurrence_weekly_until": None,
    }
    defaults.update(overrides)
    return BookingRequest(**defaults)


def test_valid_request():
    errors = validate_booking_request(make_req(), ROOMS, EXISTING)
    assert errors == []


def test_empty_id():
    errors = validate_booking_request(make_req(id="   "), ROOMS, EXISTING)
    assert any("id" in e for e in errors)


def test_duplicate_id():
    errors = validate_booking_request(make_req(id="b1"), ROOMS, {"b1"})
    assert any("already exists" in e for e in errors)


def test_unknown_room():
    errors = validate_booking_request(make_req(room_id="r99"), ROOMS, EXISTING)
    assert any("not found" in e for e in errors)


def test_empty_organiser():
    errors = validate_booking_request(make_req(organiser=""), ROOMS, EXISTING)
    assert any("organiser" in e.lower() for e in errors)


def test_end_before_start():
    errors = validate_booking_request(
        make_req(start_time="2026-10-27T10:00", end_time="2026-10-27T09:00"),
        ROOMS, EXISTING,
    )
    assert any("after" in e for e in errors)


def test_zero_duration():
    errors = validate_booking_request(
        make_req(start_time="2026-10-27T10:00", end_time="2026-10-27T10:00"),
        ROOMS, EXISTING,
    )
    assert len(errors) > 0


def test_invalid_datetime():
    errors = validate_booking_request(
        make_req(start_time="not-a-date"),
        ROOMS, EXISTING,
    )
    assert any("start_time" in e for e in errors)


def test_timezone_rejected():
    errors = validate_booking_request(
        make_req(start_time="2026-10-27T09:00+05:30"),
        ROOMS, EXISTING,
    )
    assert any("timezone" in e for e in errors)


def test_utc_z_rejected():
    errors = validate_booking_request(
        make_req(start_time="2026-10-27T09:00Z"),
        ROOMS, EXISTING,
    )
    assert any("timezone" in e for e in errors)


def test_empty_attendees():
    errors = validate_booking_request(make_req(attendees=[]), ROOMS, EXISTING)
    assert any("attendee" in e.lower() for e in errors)


def test_duplicate_attendee():
    errors = validate_booking_request(make_req(attendees=["bob", "Bob"]), ROOMS, EXISTING)
    assert any("duplicate" in e for e in errors)


def test_empty_attendee_name():
    errors = validate_booking_request(make_req(attendees=["  "]), ROOMS, EXISTING)
    assert any("empty" in e for e in errors)


def test_capacity_exceeded_in_request():
    errors = validate_booking_request(
        make_req(attendees=["a", "b", "c", "d", "e"]),
        ROOMS, EXISTING,
    )
    assert any("capacity" in e for e in errors)


def test_recurrence_until_before_start():
    errors = validate_booking_request(
        make_req(
            start_time="2026-10-27T09:00",
            recurrence_weekly_until="2026-10-20",
        ),
        ROOMS, EXISTING,
    )
    assert any("recurrence_weekly_until" in e for e in errors)


def test_recurrence_crosses_midnight():
    errors = validate_booking_request(
        make_req(
            start_time="2026-10-27T23:00",
            end_time="2026-10-28T01:00",
            recurrence_weekly_until="2026-12-31",
        ),
        ROOMS, EXISTING,
    )
    assert any("midnight" in e for e in errors)


def test_recurrence_too_long():
    errors = validate_booking_request(
        make_req(
            start_time="2026-01-01T09:00",
            recurrence_weekly_until="2035-01-01",  # > 260 weeks
        ),
        ROOMS, EXISTING,
    )
    assert any("recurrence range" in e for e in errors)


def test_to_booking_conversion():
    req = make_req()
    errors = validate_booking_request(req, ROOMS, EXISTING)
    assert errors == []
    b = to_booking(req)
    assert b.id == "b1"
    assert b.attendees == ["bob"]
    assert b.organiser == "alice"