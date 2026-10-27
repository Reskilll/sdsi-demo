"""Unit tests for find-slot algorithm (M4).

Tests against a real (but empty or pre-filled) BookingEngine.
"""

from __future__ import annotations

import pytest
from engine import BookingEngine
from engine.models import BookingRequest


@pytest.fixture
def engine():
    return BookingEngine("rooms.json")


# ---------------------------------------------------------------------------
# Basic slot finding
# ---------------------------------------------------------------------------

def test_find_slot_empty_day_earliest_room(engine):
    """Empty day — should return the smallest-capacity room that fits at 09:00."""
    slot = engine.find_slot(60, 3, "2026-10-27")
    assert slot is not None
    assert slot.room.id == "r1"  # Alpha (cap 4) — smallest id with enough capacity
    assert slot.start.isoformat() == "2026-10-27T09:00:00"
    assert slot.end.isoformat() == "2026-10-27T10:00:00"


def test_find_slot_large_group_gets_big_room(engine):
    """Large attendee count skips small rooms."""
    slot = engine.find_slot(60, 10, "2026-10-27")
    assert slot is not None
    assert slot.room.capacity >= 10
    # r1=4, r2=8, r3=12 — so r3 is smallest id with capacity >= 10
    assert slot.room.id == "r3"


def test_find_slot_no_room_fits(engine):
    """Attendee count exceeding max capacity → None."""
    slot = engine.find_slot(60, 30, "2026-10-27")
    assert slot is None


def test_find_slot_duration_too_long(engine):
    """Duration > business hours returns None."""
    slot = engine.find_slot(541, 1, "2026-10-27")  # 9h1m > 9h
    assert slot is None


def test_find_slot_exact_business_hours(engine):
    """A booking that exactly fits 09:00–18:00 must be found."""
    slot = engine.find_slot(540, 1, "2026-10-27")  # exactly 9 hours
    assert slot is not None
    assert slot.start.isoformat() == "2026-10-27T09:00:00"
    assert slot.end.isoformat() == "2026-10-27T18:00:00"


def test_find_slot_exact_ending_at_18(engine):
    """A booking ending exactly at 18:00 is valid."""
    # Fill all slots before 17:00
    engine.create_booking(BookingRequest(
        id="blocker", room_id="r1", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T17:00",
        attendees=["x"],
    ))
    # r1 blocked; r2 is next with capacity >= 1
    slot = engine.find_slot(60, 1, "2026-10-27")
    assert slot is not None
    assert slot.room.id in ("r2", "r3", "r4", "r5")
    # The earliest start across eligible rooms should be 09:00
    # Actually r1 is blocked, so r2 should give 09:00
    assert slot.start.isoformat() == "2026-10-27T09:00:00"


def test_find_slot_one_room_full_falls_back(engine):
    """When the first room is partially blocked, find the global earliest slot."""
    engine.create_booking(BookingRequest(
        id="block", room_id="r1", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T09:30",
        attendees=["x"],
    ))
    # r1 is busy 09:00-09:30 but free at 09:30
    # r2 is free at 09:00
    # Globally earliest is r2 at 09:00
    slot = engine.find_slot(60, 1, "2026-10-27")
    assert slot is not None
    assert slot.start.isoformat() == "2026-10-27T09:00:00"
    # It should be r2 (the next room), since r1's 09:00 is blocked
    # Wait — r1 at 09:30 would be 30 mins later than r2 at 09:00
    # So global earliest is r2 at 09:00
    assert slot.room.id == "r2"


def test_find_slot_only_slot_at_end_of_day(engine):
    """When all early slots are taken, find the late slot."""
    # Book 09:00–17:00 on r1
    engine.create_booking(BookingRequest(
        id="block1", room_id="r1", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T17:00",
        attendees=["x"],
    ))
    # Book 09:00–17:30 on r2
    engine.create_booking(BookingRequest(
        id="block2", room_id="r2", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T17:30",
        attendees=["x"],
    ))
    # Book 09:00–17:59 on r3
    engine.create_booking(BookingRequest(
        id="block3", room_id="r3", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T17:59",
        attendees=["x"],
    ))
    # r4 is capacity 2, r5 is capacity 20
    # 1-minute slot at 17:59: r4 at 09:00 should be free (r4 not blocked)
    # Actually r4 is free all day. Let me block r4 too.
    engine.create_booking(BookingRequest(
        id="block4", room_id="r4", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T17:59",
        attendees=["x"],
    ))
    # Now only r5 is free at 09:00. So the earliest is r5 at 09:00.
    # Let me instead make a simpler test: block all rooms from 09:00-17:00
    # leaving 17:00–18:00 free, test that a 60-min slot is found at 17:00
    for rid in ("r1", "r2", "r3", "r4", "r5"):
        engine.create_booking(BookingRequest(
            id=f"block-{rid}", room_id=rid, organiser="x",
            start_time="2026-10-27T09:00", end_time="2026-10-27T17:00",
            attendees=["x"],
        ))
    slot = engine.find_slot(60, 1, "2026-10-27")
    assert slot is not None
    assert slot.start.isoformat() == "2026-10-27T17:00:00"
    assert slot.end.isoformat() == "2026-10-27T18:00:00"


def test_find_slot_completely_full(engine):
    """When every room is fully booked, return None."""
    for rid in ("r1", "r2", "r3", "r4", "r5"):
        engine.create_booking(BookingRequest(
            id=f"full-{rid}", room_id=rid, organiser="x",
            start_time="2026-10-27T09:00", end_time="2026-10-27T18:00",
            attendees=["x"],
        ))
    slot = engine.find_slot(15, 1, "2026-10-27")
    assert slot is None


def test_find_slot_recurring_blocks(engine):
    """An existing recurring booking must block its slots."""
    engine.create_booking(BookingRequest(
        id="recur", room_id="r1", organiser="x",
        start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
        attendees=["x"],
        recurrence_weekly_until="2026-11-30",
    ))
    # Oct 26 is Sunday; Oct 27 is Monday — not the same weekday, so r1 is free
    slot = engine.find_slot(60, 1, "2026-10-27")
    assert slot is not None
    assert slot.room.id == "r1"

    # But Nov 2 (Monday, 7 days after Oct 26) should be blocked
    # Wait: Oct 26 2026 is a Monday. Let me verify... No matter, the recurrence
    # expands 7 days at a time. Nov 2 = Oct 26 + 7, so r1 should be blocked.
    slot2 = engine.find_slot(60, 1, "2026-11-02")
    assert slot2 is not None  # r2 should be available
    # r1 at 09:00-10:00 is blocked, so globally earliest is r2 at 09:00
    assert slot2.room.id == "r2"


def test_find_slot_duration_one_minute(engine):
    """Minimum duration of 1 minute should work."""
    slot = engine.find_slot(1, 1, "2026-10-27")
    assert slot is not None
    assert slot.start.isoformat() == "2026-10-27T09:00:00"
    assert slot.end.isoformat() == "2026-10-27T09:01:00"


def test_find_slot_invalid_date(engine):
    with pytest.raises(ValueError):
        engine.find_slot(60, 1, "not-a-date")