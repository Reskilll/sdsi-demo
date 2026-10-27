"""Tests for weekly recurrence (M5)."""

from __future__ import annotations

import pytest
from engine import BookingEngine
from engine.models import BookingRequest
from engine.recurrence import expand_occurrences


@pytest.fixture
def engine():
    return BookingEngine("rooms.json")


# ---------------------------------------------------------------------------
# Recurrence expansion correctness
# ---------------------------------------------------------------------------

def test_expand_non_recurring():
    engine2 = BookingEngine("rooms.json")
    r = engine2.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    b = r.booking
    occs = expand_occurrences(b)
    assert len(occs) == 1
    assert occs[0].start_time == b.start_time


def test_expand_recurring_two_weeks():
    engine2 = BookingEngine("rooms.json")
    r = engine2.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["a"],
        recurrence_weekly_until="2026-11-02",
    ))
    b = r.booking
    occs = expand_occurrences(b)
    # Oct 26, Nov 2 = 2 occurrences
    assert len(occs) == 2
    assert occs[0].start_time.date().isoformat() == "2026-10-26"
    assert occs[1].start_time.date().isoformat() == "2026-11-02"
    # Times preserved
    for occ in occs:
        assert occ.start_time.hour == 9
        assert occ.end_time.hour == 10


def test_recurrence_until_same_day(engine):
    """recurrence_weekly_until same as start date = 1 occurrence."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
        recurrence_weekly_until="2026-10-27",
    ))
    assert r.success
    occs = expand_occurrences(r.booking)
    assert len(occs) == 1


def test_recurrence_until_weekday_mismatch(engine):
    """recurrence_weekly_until on a different weekday — expansion stops
    at the last occurrence on or before the until date.

    Example: start = Monday Oct 26, until = Wednesday Oct 28
    Occurrences: Oct 26 (Mon).  Nov 2 (Mon) > Oct 28, so stop.
    Only 1 occurrence.
    """
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["a"],
        recurrence_weekly_until="2026-10-28",
    ))
    assert r.success
    occs = expand_occurrences(r.booking)
    assert len(occs) == 1  # Only Oct 26; Nov 2 > Oct 28


# ---------------------------------------------------------------------------
# Conflict reporting for recurrences
# ---------------------------------------------------------------------------

def test_recurrence_conflict_single_occurrence(engine):
    """Create a recurring booking, then try to create another recurring that
    overlaps one of its occurrences."""
    engine.create_booking(BookingRequest(
        id="rec1", room_id="r1", organiser="alice",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["alice"],
        recurrence_weekly_until="2026-11-30",
    ))
    # rec2 starts Oct 27 (Tue) and recurs. Oct 27 ≠ Monday, so no conflict on
    # Oct 26 occurrences. Let me make rec2 start on a Monday that conflicts.
    # rec2 starts Nov 2 (which is a Monday — Oct 26 + 7)
    r2 = engine.create_booking(BookingRequest(
        id="rec2", room_id="r1", organiser="bob",
        start_time="2026-11-02T09:30", end_time="2026-11-02T10:30",
        attendees=["bob"],
        recurrence_weekly_until="2026-11-30",
    ))
    # rec2's first occurrence (Nov 2 at 09:30-10:30) overlaps rec1's second
    # occurrence (Nov 2 at 09:00-10:00) — overlap!
    assert not r2.success
    assert len(r2.conflicts) >= 1
    assert "overlap" in r2.conflicts[0].reason


def test_recurrence_conflict_multiple_dates(engine):
    """Recurring booking that conflicts on multiple separate dates."""
    # Create two non-recurring bookings on different Mondays
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="x",
        start_time="2026-11-02T10:00", end_time="2026-11-02T11:00",
        attendees=["x"],
    ))
    engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="x",
        start_time="2026-11-09T10:00", end_time="2026-11-09T11:00",
        attendees=["x"],
    ))
    # Now a recurring booking that runs 09:30-10:30 every Monday
    r = engine.create_booking(BookingRequest(
        id="rec", room_id="r1", organiser="y",
        start_time="2026-11-02T09:30", end_time="2026-11-02T10:30",
        attendees=["y"],
        recurrence_weekly_until="2026-11-16",
    ))
    assert not r.success
    # Should report conflicts on Nov 2 (overlaps b1) and Nov 9 (overlaps b2)
    assert len(r.conflicts) >= 2
    dates = {c.occurrence_date.isoformat() for c in r.conflicts}
    assert "2026-11-02" in dates
    assert "2026-11-09" in dates


def test_recurrence_atomic_rejection(engine):
    """If any occurrence conflicts, nothing is created."""
    engine.create_booking(BookingRequest(
        id="blocker", room_id="r1", organiser="x",
        start_time="2026-11-09T09:45", end_time="2026-11-09T11:00",
        attendees=["x"],
    ))
    # Candidate's Nov 9 occurrence (09:30–10:00) overlaps blocker (09:45–11:00)
    r = engine.create_booking(BookingRequest(
        id="rec", room_id="r1", organiser="y",
        start_time="2026-11-02T09:30", end_time="2026-11-02T10:00",
        attendees=["y"],
        recurrence_weekly_until="2026-11-16",
    ))
    assert not r.success
    # rec must not exist
    with pytest.raises(KeyError):
        engine.read_booking("rec")


def test_recurrence_capacity_violation(engine):
    """Recurring booking where room capacity is exceeded."""
    # r4 has capacity 2
    r = engine.create_booking(BookingRequest(
        id="rec", room_id="r4", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a", "b", "c"],  # 3 > 2
        recurrence_weekly_until="2026-11-30",
    ))
    assert not r.success
    assert any("capacity" in e for e in r.errors)


def test_recurrence_boundary_inclusive(engine):
    """recurrence_weekly_until is inclusive — the occurrence on that date is
    included if it matches the weekday."""
    # Oct 26 2026 is Monday. Oct 26 + 7 = Nov 2.
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["a"],
        recurrence_weekly_until="2026-11-02",
    ))
    assert r.success
    occs = expand_occurrences(r.booking)
    assert len(occs) == 2
    assert occs[-1].start_time.date().isoformat() == "2026-11-02"


def test_recurrence_self_conflict_detection(engine):
    """A recurring booking's own occurrences should not overlap each other
    on the same room. This is a structural check: weekly recurrences naturally
    don't overlap themselves (same time, different days). But we should verify
    two different recurring bookings that conflict are caught."""
    # Create a recurring booking
    engine.create_booking(BookingRequest(
        id="rec1", room_id="r1", organiser="a",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["a"],
        recurrence_weekly_until="2026-11-30",
    ))
    # Second recurring booking whose first occurrence doesn't overlap
    # but a later occurrence does (same weekday, overlapping times)
    r2 = engine.create_booking(BookingRequest(
        id="rec2", room_id="r1", organiser="b",
        start_time="2026-11-02T09:30", end_time="2026-11-02T11:00",
        attendees=["b"],
        recurrence_weekly_until="2026-11-30",
    ))
    # rec2's Nov 2 at 09:30-11:00 overlaps rec1's Nov 2 at 09:00-10:00
    assert not r2.success
    assert len(r2.conflicts) >= 1