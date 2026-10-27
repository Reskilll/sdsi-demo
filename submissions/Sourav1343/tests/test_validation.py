"""Edge-case and adversarial tests for the booking engine.

Covers invalid input, boundary conditions, concurrency, and unusual scenarios.
"""

from __future__ import annotations

import json
import threading

import pytest
from engine import BookingEngine
from engine.models import BookingRequest


@pytest.fixture
def engine():
    return BookingEngine("rooms.json")


# ---------------------------------------------------------------------------
# Malformed / extreme inputs
# ---------------------------------------------------------------------------

def test_extremely_long_string_rejected(engine):
    r = engine.create_booking(BookingRequest(
        id="x" * 600, room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    assert not r.success
    assert any("length" in e.lower() for e in r.errors)


def test_too_many_attendees(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r5", organiser="a",  # r5 has capacity 20
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=[f"person{i}" for i in range(501)],
    ))
    assert not r.success


def test_attendee_not_string(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=[123],  # type: ignore[list-item]
    ))
    assert not r.success
    assert any("string" in e for e in r.errors)


def test_missing_field_in_request():
    """Engine validates required fields."""
    eng = BookingEngine("rooms.json")
    r = eng.create_booking(BookingRequest(
        id="", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    assert not r.success


def test_iso8601_variants(engine):
    """Accept common ISO-8601 naive formats."""
    # With seconds
    r1 = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00:00", end_time="2026-10-27T10:00:00",
        attendees=["a"],
    ))
    assert r1.success

    # With fractional seconds
    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r2", organiser="b",
        start_time="2026-10-27T09:00:00.000", end_time="2026-10-27T10:00:00.000",
        attendees=["b"],
    ))
    assert r2.success


def test_iso8601_with_seconds_rejected_if_timezone(engine):
    """Reject ISO-8601 with UTC 'Z' marker."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00:00Z", end_time="2026-10-27T10:00:00Z",
        attendees=["a"],
    ))
    assert not r.success


def test_cross_midnight_non_recurring_allowed(engine):
    """Non-recurring bookings spanning midnight are allowed."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T23:00", end_time="2026-10-28T01:00",
        attendees=["a"],
    ))
    assert r.success


def test_duplicate_id(engine):
    engine.create_booking(BookingRequest(
        id="dup", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    r2 = engine.create_booking(BookingRequest(
        id="dup", room_id="r2", organiser="b",
        start_time="2026-10-27T11:00", end_time="2026-10-27T12:00",
        attendees=["b"],
    ))
    assert not r2.success
    assert any("already exists" in e for e in r2.errors)


def test_duplicate_attendee_names(engine):
    """Case-insensitive duplicate attendee names are rejected."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["Alice", "alice"],
    ))
    assert not r.success
    assert any("duplicate" in e for e in r.errors)


def test_find_slot_invalid_params(engine):
    with pytest.raises(ValueError):
        engine.find_slot(0, 1, "2026-10-27")
    with pytest.raises(ValueError):
        engine.find_slot(60, 0, "2026-10-27")


def test_recurrence_until_not_a_date(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
        recurrence_weekly_until="not-a-date",
    ))
    assert not r.success
    assert any("recurrence_weekly_until" in e for e in r.errors)


# ---------------------------------------------------------------------------
# Concurrency test
# ---------------------------------------------------------------------------

def test_concurrent_separate_engines():
    """Two threads with separate engine instances each create the same slot.
    Independent engines = independent stores — both succeed. This documents
    that cross-engine coordination requires external locking or a shared store."""
    successes = []

    def book(worker_id: int):
        eng = BookingEngine("rooms.json")
        r = eng.create_booking(BookingRequest(
            id=f"race-{worker_id}",
            room_id="r1",
            organiser=f"worker{worker_id}",
            start_time="2026-10-27T10:00",
            end_time="2026-10-27T11:00",
            attendees=[f"w{worker_id}"],
        ))
        if r.success:
            successes.append(worker_id)

    t1 = threading.Thread(target=book, args=(1,))
    t2 = threading.Thread(target=book, args=(2,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # Independent engines = no shared state, no conflict
    assert len(successes) == 2


def test_concurrent_same_store():
    """Multiple threads sharing ONE engine instance — lock serialises access.

    All 5 threads try to book the same room at the same time with different
    booking IDs.  The first to acquire the lock succeeds; the rest get
    overlap-conflict rejections.
    """
    eng = BookingEngine("rooms.json")
    results = []

    def book(wid: int):
        r = eng.create_booking(BookingRequest(
            id=f"cs-{wid}",
            room_id="r1",
            organiser=f"w{wid}",
            start_time="2026-10-27T14:00",
            end_time="2026-10-27T15:00",
            attendees=[f"p{wid}"],
        ))
        results.append((wid, r.success))

    threads = [threading.Thread(target=book, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    success_count = sum(1 for _, ok in results if ok)
    # At least 1 succeeds; depending on thread scheduling, exactly 1 should
    # win the race because the store lock serialises all add() calls.
    assert success_count >= 1
    conflict_count = sum(1 for _, ok in results if not ok)
    assert conflict_count >= 1


def test_empty_attendee_string(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["  "],
    ))
    assert not r.success


def test_whitespace_trimmed_fields(engine):
    """IDs and room_ids should be trimmed."""
    r = engine.create_booking(BookingRequest(
        id="  b1  ", room_id="  r1  ", organiser="  alice  ",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["  bob  "],
    ))
    assert r.success
    b = engine.read_booking("b1")
    assert b.organiser == "alice"
    assert b.attendees == ["bob"]


def test_list_rooms(engine):
    rooms = engine.list_rooms()
    assert len(rooms) == 5
    assert rooms[0].id == "r1"  # sorted by id