"""Public API: :class:`BookingEngine`.

This is the single entry-point consumers should import.  It orchestrates the
store, validator, recurrence expansion, and find-slot algorithm behind a
stable, documented interface.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Optional

from .finder import find_available_slot
from .models import Booking, BookingRequest, BookingResult, Conflict, Room, Slot
from .recurrence import expand_occurrences
from .store import InMemoryStore
from .validator import (
    assert_no_overlaps,
    to_booking,
    validate_booking_request,
)


class BookingEngine:
    """High-level booking engine.

    Parameters
    ----------
    rooms_file:
        Path to a JSON file containing the room catalogue (``rooms.json``).
    data_file:
        Optional path to a JSON persistence file.  If it exists it is loaded
        on startup; subsequent saves go here.  Pass ``None`` for an in-memory-
        only engine.
    """

    def __init__(self, rooms_file: str, data_file: Optional[str] = None) -> None:
        rooms = _load_rooms(rooms_file)
        self._store = InMemoryStore(rooms, data_file=data_file)
        self._data_file = data_file

    # ------------------------------------------------------------------
    # Room catalogue
    # ------------------------------------------------------------------

    def list_rooms(self) -> list[Room]:
        """Return every room, sorted by id."""
        return self._store.list_rooms()

    # ------------------------------------------------------------------
    # M1: CRUD
    # ------------------------------------------------------------------

    def create_booking(self, req: BookingRequest) -> BookingResult:
        """Validate and create a booking (M1)."""
        errors = validate_booking_request(
            req, self._store.list_room_map(), self._all_booking_ids(),
        )
        if errors:
            return BookingResult(success=False, errors=errors)

        booking = to_booking(req)

        # Check each occurrence against existing bookings (M2, M5)
        occurrences = expand_occurrences(booking)
        existing = self._store.list_all()
        conflicts = assert_no_overlaps(booking, occurrences, existing)
        if conflicts:
            return BookingResult(success=False, conflicts=conflicts)

        try:
            self._store.add(booking)
            self._save_if_configured()
        except ValueError as exc:
            return BookingResult(success=False, errors=[str(exc)])

        return BookingResult(success=True, booking=booking)

    def read_booking(self, booking_id: str) -> Booking:
        """Return a booking by id (M1).  Raises :exc:`KeyError` if not found."""
        return self._store.get(booking_id)

    def update_booking(self, req: BookingRequest) -> BookingResult:
        """Replace an existing booking with a new one (M1).

        The booking being updated is excluded from conflict checks so updating
        a non-conflicting field (e.g. organiser) always succeeds.
        """
        # Must already exist
        try:
            self._store.get(req.id.strip())
        except KeyError:
            return BookingResult(
                success=False,
                errors=[f"booking id '{req.id.strip()}' not found — use create for new bookings"],
            )

        # Validate the replacement, excluding self from id-uniqueness check
        existing_ids = self._all_booking_ids() - {req.id.strip()}
        errors = validate_booking_request(
            req, self._store.list_room_map(), existing_ids,
        )
        if errors:
            return BookingResult(success=False, errors=errors)

        booking = to_booking(req)

        # Check overlaps, excluding self
        occurrences = expand_occurrences(booking)
        all_existing = self._store.list_all()
        existing_without_self = [b for b in all_existing if b.id != booking.id]
        conflicts = assert_no_overlaps(booking, occurrences, existing_without_self)
        if conflicts:
            return BookingResult(success=False, conflicts=conflicts)

        try:
            self._store.update(booking)
            self._save_if_configured()
        except Exception as exc:
            return BookingResult(success=False, errors=[str(exc)])

        return BookingResult(success=True, booking=booking)

    def delete_booking(self, booking_id: str) -> None:
        """Delete a booking (M1).  Raises :exc:`KeyError` if not found."""
        self._store.delete(booking_id)
        self._save_if_configured()

    # ------------------------------------------------------------------
    # M4: find-slot
    # ------------------------------------------------------------------

    def find_slot(
        self, duration_minutes: int, attendee_count: int, date_str: str,
    ) -> Optional[Slot]:
        """Return the globally earliest available slot (M4).

        Parameters
        ----------
        duration_minutes:
            How many minutes the booking needs.
        attendee_count:
            Minimum room capacity required.
        date_str:
            ISO-8601 date string, e.g. ``"2026-11-01"``.

        Returns
        -------
        Slot or None
        """
        try:
            target_date = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            raise ValueError(f"invalid date: {date_str!r} — expected ISO-8601 (e.g. 2026-11-01)")

        if duration_minutes < 1:
            raise ValueError("duration_minutes must be >= 1")
        if attendee_count < 1:
            raise ValueError("attendee_count must be >= 1")

        return find_available_slot(
            self._store, duration_minutes, attendee_count, target_date,
        )

    # ------------------------------------------------------------------
    # Utility queries
    # ------------------------------------------------------------------

    def list_bookings(
        self, room_id: Optional[str] = None, date_str: Optional[str] = None,
    ) -> list[Booking]:
        """Return bookings, optionally filtered by room and/or date.

        When *date_str* is given recurring bookings are expanded to that date.
        """
        if room_id and date_str:
            target = date.fromisoformat(date_str)
            from .recurrence import expand_to_date
            result: list[Booking] = []
            for b in self._store.bookings_for_room(room_id):
                occ = expand_to_date(b, target)
                if occ:
                    result.append(occ)
            return result
        if room_id:
            return self._store.bookings_for_room(room_id)
        if date_str:
            return self._store.bookings_for_date(date.fromisoformat(date_str))
        return self._store.list_all()

    def save(self) -> None:
        """Persist current state to the configured data file (if any)."""
        self._save_if_configured()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_booking_ids(self) -> set[str]:
        return {b.id for b in self._store.list_all()}

    def _save_if_configured(self) -> None:
        if self._data_file:
            self._store.save(self._data_file)


def _load_rooms(path: str) -> list[Room]:
    """Load the room catalogue from *path* (JSON)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"rooms file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    rooms: list[Room] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path}[{i}] must be a JSON object")
        rooms.append(
            Room(
                id=_require_str(item, "id", path, i),
                name=_require_str(item, "name", path, i),
                capacity=_require_int(item, "capacity", path, i),
            )
        )
    return rooms


def _require_str(item: dict, key: str, path: str, i: int) -> str:
    if key not in item or not isinstance(item[key], str) or not item[key].strip():
        raise ValueError(f"{path}[{i}].{key} must be a non-empty string")
    return item[key].strip()


def _require_int(item: dict, key: str, path: str, i: int) -> int:
    if key not in item or not isinstance(item[key], (int, float)) or item[key] < 0:
        raise ValueError(f"{path}[{i}].{key} must be a non-negative integer")
    return int(item[key])