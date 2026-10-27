"""Thread-safe in-memory booking store with atomic JSON persistence.

All public mutation methods are guarded by a re-entrant lock so the store is
safe to use from multiple threads when the same :class:`InMemoryStore` instance
is shared.
"""

from __future__ import annotations

import json
import os
import threading
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import Booking, Room
from .validator import overlaps


class InMemoryStore:
    """A lock-protected, in-memory collection of rooms and bookings.

    The store is initialised with a fixed room list.  Bookings are mutable via
    CRUD operations; the room list is immutable after construction.

    Parameters
    ----------
    rooms:
        The room catalogue — typically loaded from ``rooms.json``.
    data_file:
        When provided, :meth:`load` is called immediately to restore persisted
        state.  When ``None`` the store starts empty.
    """

    def __init__(self, rooms: list[Room], data_file: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._rooms: dict[str, Room] = {r.id: r for r in rooms}
        self._bookings: dict[str, Booking] = {}
        self._data_file = data_file
        if data_file and os.path.isfile(data_file):
            self.load(data_file)

    # ------------------------------------------------------------------
    # Room access (read-only)
    # ------------------------------------------------------------------

    def get_room(self, room_id: str) -> Room:
        """Return the :class:`Room` for *room_id*, or raise :exc:`KeyError`."""
        with self._lock:
            return self._rooms[room_id]

    def get_rooms_by_capacity(self, min_capacity: int) -> list[Room]:
        """Return every room with capacity ≥ *min_capacity*, sorted by id."""
        with self._lock:
            result = [r for r in self._rooms.values() if r.capacity >= min_capacity]
            result.sort(key=lambda r: r.id)
            return result

    def list_rooms(self) -> list[Room]:
        """Return all rooms sorted by id."""
        with self._lock:
            result = list(self._rooms.values())
            result.sort(key=lambda r: r.id)
            return result

    def list_room_ids(self) -> set[str]:
        """Return the set of known room ids (for validation)."""
        with self._lock:
            return set(self._rooms.keys())

    def list_room_map(self) -> dict[str, Room]:
        """Return the id → Room mapping (for capacity validation)."""
        with self._lock:
            return dict(self._rooms)

    # ------------------------------------------------------------------
    # Booking CRUD
    # ------------------------------------------------------------------

    def add(self, booking: Booking) -> None:
        """Insert *booking*; raises :exc:`ValueError` if the id already exists."""
        with self._lock:
            if booking.id in self._bookings:
                raise ValueError(f"booking id '{booking.id}' already exists")
            self._bookings[booking.id] = booking

    def get(self, booking_id: str) -> Booking:
        """Return the :class:`Booking` for *booking_id*, or raise :exc:`KeyError`."""
        with self._lock:
            return self._bookings[booking_id]

    def update(self, booking: Booking) -> None:
        """Replace the stored booking with the same id.

        Raises :exc:`KeyError` if the id does not exist.
        """
        with self._lock:
            if booking.id not in self._bookings:
                raise KeyError(f"booking id '{booking.id}' not found")
            self._bookings[booking.id] = booking

    def delete(self, booking_id: str) -> None:
        """Remove the booking with *booking_id*, or raise :exc:`KeyError`."""
        with self._lock:
            if booking_id not in self._bookings:
                raise KeyError(f"booking id '{booking_id}' not found")
            del self._bookings[booking_id]

    def list_all(self) -> list[Booking]:
        """Return every stored booking template."""
        with self._lock:
            return list(self._bookings.values())

    # ------------------------------------------------------------------
    # Slot availability queries
    # ------------------------------------------------------------------

    def is_slot_free(
        self, room_id: str, start: datetime, end: datetime,
        exclude_booking_id: Optional[str] = None,
    ) -> bool:
        """Check that no booking for *room_id* overlaps *[start, end)*.

        When *exclude_booking_id* is set (used during update) that booking is
        ignored so the slot is checked against *other* bookings.
        """
        with self._lock:
            for b in self._bookings.values():
                if exclude_booking_id is not None and b.id == exclude_booking_id:
                    continue
                if b.room_id != room_id:
                    continue
                if overlaps(b.start_time, b.end_time, start, end):
                    return False
            return True

    def bookings_for_room(self, room_id: str) -> list[Booking]:
        """Return every booking for *room_id*."""
        with self._lock:
            return [b for b in self._bookings.values() if b.room_id == room_id]

    def bookings_for_date(self, target_date: date) -> list[Booking]:
        """Return every booking (including recurrences) active on *target_date*."""
        from .recurrence import expand_to_date

        with self._lock:
            result: list[Booking] = []
            for b in self._bookings.values():
                occ = expand_to_date(b, target_date)
                if occ is not None:
                    result.append(occ)
            return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, filepath: str) -> None:
        """Atomically persist the current booking set to *filepath*.

        Writes to a temporary file in the same directory, then renames it over
        *filepath* so a crash during write never corrupts an existing file.
        """
        data = self._serialize()
        dirname = os.path.dirname(filepath) or "."
        fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, filepath)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def load(self, filepath: str) -> None:
        """Load (merge) bookings from a JSON file previously written by :meth:`save`.

        Existing bookings with the same id are overwritten.  The file must be a
        JSON array of booking objects.
        """
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("persistence file must contain a JSON array")

        restored = 0
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("each item in persistence file must be a JSON object")
            b = Booking(
                id=item["id"],
                room_id=item["room_id"],
                organiser=item["organiser"],
                start_time=datetime.fromisoformat(item["start_time"]),
                end_time=datetime.fromisoformat(item["end_time"]),
                attendees=item["attendees"],
                recurrence_weekly_until=(
                    date.fromisoformat(item["recurrence_weekly_until"])
                    if item.get("recurrence_weekly_until")
                    else None
                ),
            )
            with self._lock:
                self._bookings[b.id] = b
            restored += 1

    def _serialize(self) -> list[dict]:
        """Encode all bookings as a plain JSON structure."""
        with self._lock:
            return [
                {
                    "id": b.id,
                    "room_id": b.room_id,
                    "organiser": b.organiser,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "attendees": b.attendees,
                    "recurrence_weekly_until": (
                        b.recurrence_weekly_until.isoformat()
                        if b.recurrence_weekly_until
                        else None
                    ),
                }
                for b in self._bookings.values()
            ]