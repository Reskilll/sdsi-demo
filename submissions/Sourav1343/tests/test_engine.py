"""Integration tests for CRUD operations (M1, M3) via BookingEngine."""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from engine import BookingEngine
from engine.models import BookingRequest


@pytest.fixture
def engine():
    return BookingEngine("rooms.json")


# ---------------------------------------------------------------------------
# M1: Create / Read / Update / Delete
# ---------------------------------------------------------------------------

def test_create_and_read(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["bob", "carol"],
    ))
    assert r.success
    assert r.booking is not None
    assert r.booking.id == "b1"

    b = engine.read_booking("b1")
    assert b.organiser == "alice"
    assert b.attendees == ["bob", "carol"]


def test_delete_and_recreate(engine):
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    engine.delete_booking("b1")
    with pytest.raises(KeyError):
        engine.read_booking("b1")
    # Recreate should work
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="bob",
        start_time="2026-10-27T10:00", end_time="2026-10-27T11:00",
        attendees=["bob"],
    ))
    assert r.success


def test_update_non_conflicting(engine):
    """Update organiser without changing time/room must succeed."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    r = engine.update_booking(BookingRequest(
        id="b1", room_id="r1", organiser="bob",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    assert r.success
    assert engine.read_booking("b1").organiser == "bob"


def test_update_nonexistent(engine):
    r = engine.update_booking(BookingRequest(
        id="no-such", room_id="r1", organiser="x",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["x"],
    ))
    assert not r.success


def test_delete_nonexistent(engine):
    with pytest.raises(KeyError):
        engine.delete_booking("no-such")


def test_list_all(engine):
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    engine.create_booking(BookingRequest(
        id="b2", room_id="r2", organiser="b",
        start_time="2026-10-27T10:00", end_time="2026-10-27T11:00",
        attendees=["b"],
    ))
    bookings = engine.list_bookings()
    assert len(bookings) == 2


def test_list_by_room(engine):
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a"],
    ))
    engine.create_booking(BookingRequest(
        id="b2", room_id="r2", organiser="b",
        start_time="2026-10-27T10:00", end_time="2026-10-27T11:00",
        attendees=["b"],
    ))
    assert len(engine.list_bookings(room_id="r1")) == 1
    assert len(engine.list_bookings(room_id="r2")) == 1
    assert len(engine.list_bookings(room_id="r99")) == 0


# ---------------------------------------------------------------------------
# M3: Capacity validation
# ---------------------------------------------------------------------------

def test_capacity_exact_boundary(engine):
    """Room r1 has capacity 4 — exactly 4 attendees must succeed."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a", "b", "c", "d"],
    ))
    assert r.success


def test_capacity_exceeded(engine):
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r4", organiser="a",  # Delta, capacity 2
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a", "b", "c"],
    ))
    assert not r.success
    assert any("capacity" in e for e in r.errors)


def test_capacity_boundary_r4(engine):
    """Delta has capacity 2."""
    r = engine.create_booking(BookingRequest(
        id="b1", room_id="r4", organiser="a",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["a", "b"],
    ))
    assert r.success


# ---------------------------------------------------------------------------
# M3: rooms.json correctness
# ---------------------------------------------------------------------------

def test_rooms_loaded(engine):
    rooms = engine.list_rooms()
    assert len(rooms) == 5
    ids = {r.id for r in rooms}
    assert ids == {"r1", "r2", "r3", "r4", "r5"}


# ---------------------------------------------------------------------------
# Update rollback
# ---------------------------------------------------------------------------

def test_update_rollback_on_overlap(engine):
    """If update fails, the original booking must be preserved."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T11:00", end_time="2026-10-27T12:00",
        attendees=["bob"],
    ))
    # Try to move b1 to overlap b2 — must fail
    r = engine.update_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T11:30", end_time="2026-10-27T12:30",
        attendees=["alice"],
    ))
    assert not r.success
    # b1 must still have its original time
    b1 = engine.read_booking("b1")
    assert b1.start_time.isoformat() == "2026-10-27T09:00:00"


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------

def test_persistence_round_trip():
    rooms_file = "rooms.json"
    # Create in temp dir with a copy of rooms.json
    with tempfile.TemporaryDirectory() as td:
        import shutil
        rooms_path = os.path.join(td, "rooms.json")
        data_path = os.path.join(td, "data.json")
        shutil.copy(rooms_file, rooms_path)

        # Engine 1: create bookings, save
        eng1 = BookingEngine(rooms_path, data_file=data_path)
        eng1.create_booking(BookingRequest(
            id="b1", room_id="r1", organiser="alice",
            start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
            attendees=["alice"],
        ))
        eng1.save()

        # Engine 2: reload from same file
        eng2 = BookingEngine(rooms_path, data_file=data_path)
        b = eng2.read_booking("b1")
        assert b.organiser == "alice"


def test_persistence_recurring_round_trip():
    rooms_file = "rooms.json"
    with tempfile.TemporaryDirectory() as td:
        import shutil
        rooms_path = os.path.join(td, "rooms.json")
        data_path = os.path.join(td, "data.json")
        shutil.copy(rooms_file, rooms_path)

        eng1 = BookingEngine(rooms_path, data_file=data_path)
        eng1.create_booking(BookingRequest(
            id="rec1", room_id="r1", organiser="alice",
            start_time="2026-10-26T09:00", end_time="2026-10-26T10:00",
            attendees=["alice"],
            recurrence_weekly_until="2026-12-31",
        ))
        eng1.save()

        eng2 = BookingEngine(rooms_path, data_file=data_path)
        b = eng2.read_booking("rec1")
        assert b.is_recurring()
        assert b.recurrence_weekly_until.isoformat() == "2026-12-31"


def test_malformed_persistence_file():
    rooms_file = "rooms.json"
    with tempfile.TemporaryDirectory() as td:
        import shutil
        rooms_path = os.path.join(td, "rooms.json")
        data_path = os.path.join(td, "data.json")
        shutil.copy(rooms_file, rooms_path)

        # Write garbage
        with open(data_path, "w") as f:
            f.write("not json")

        with pytest.raises(Exception):
            BookingEngine(rooms_path, data_file=data_path)