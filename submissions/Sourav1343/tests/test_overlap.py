"""Integration tests for overlap rules (M2) using the BookingEngine.

Covers: same-room overlap rejection, back-to-back allowed, different-room
simultaneous bookings allowed.
"""

from __future__ import annotations

import pytest
from engine import BookingEngine
from engine.models import BookingRequest


@pytest.fixture
def engine():
    return BookingEngine("rooms.json")


def test_back_to_back_same_room_allowed(engine):
    """Back-to-back bookings on the same room must succeed."""
    r1 = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    assert r1.success

    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T10:00", end_time="2026-10-27T11:00",
        attendees=["bob"],
    ))
    assert r2.success


def test_overlap_same_room_rejected(engine):
    """Overlapping bookings on the same room must be rejected."""
    r1 = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    assert r1.success

    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T09:30", end_time="2026-10-27T10:30",
        attendees=["bob"],
    ))
    assert not r2.success
    assert len(r2.conflicts) >= 1
    assert "overlap" in r2.conflicts[0].reason


def test_overlap_completely_contains(engine):
    """A booking completely inside another must be rejected."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T12:00",
        attendees=["alice"],
    ))
    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T10:00", end_time="2026-10-27T11:00",
        attendees=["bob"],
    ))
    assert not r2.success


def test_different_room_simultaneous_allowed(engine):
    """Simultaneous bookings on different rooms must be allowed."""
    r1 = engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    assert r1.success

    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r2", organiser="bob",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["bob"],
    ))
    assert r2.success


def test_overlap_exact_same_time_rejected(engine):
    """Two bookings for the exact same slot on same room must be rejected."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["alice"],
    ))
    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
        attendees=["bob"],
    ))
    assert not r2.success


def test_touching_at_boundary_allowed(engine):
    """Back-to-back touching at minute boundaries must be allowed."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T09:01",
        attendees=["alice"],
    ))
    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T09:01", end_time="2026-10-27T09:02",
        attendees=["bob"],
    ))
    assert r2.success


def test_overlap_edge_covers_boundary(engine):
    """Overlap at minute-level boundary must be caught."""
    engine.create_booking(BookingRequest(
        id="b1", room_id="r1", organiser="alice",
        start_time="2026-10-27T09:00", end_time="2026-10-27T09:30",
        attendees=["alice"],
    ))
    r2 = engine.create_booking(BookingRequest(
        id="b2", room_id="r1", organiser="bob",
        start_time="2026-10-27T09:29", end_time="2026-10-27T10:00",
        attendees=["bob"],
    ))
    assert not r2.success