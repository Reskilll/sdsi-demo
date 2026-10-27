"""JSON-file persistence with an in-process lock for thread-safe writes."""
import json
import threading
from pathlib import Path
from typing import Optional

from .models import Booking, Room

_lock = threading.Lock()


class Store:
    """Loads rooms once; keeps bookings in a JSON file."""

    def __init__(self, rooms_file: Path, bookings_file: Path) -> None:
        self._rooms_file = rooms_file
        self._bookings_file = bookings_file
        self.rooms: dict[str, Room] = {
            r.id: r for r in [Room(**d) for d in json.loads(rooms_file.read_text())]
        }

    # -- rooms -----------------------------------------------------------
    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def rooms_for_capacity(self, min_capacity: int) -> list[Room]:
        return sorted(
            (r for r in self.rooms.values() if r.capacity >= min_capacity),
            key=lambda r: (r.capacity, r.id),
        )

    # -- bookings --------------------------------------------------------
    def _read(self) -> dict[str, Booking]:
        if not self._bookings_file.exists():
            return {}
        return {
            b.id: b for b in [Booking(**d) for d in json.loads(self._bookings_file.read_text())]
        }

    def _write(self, bookings: dict[str, Booking]) -> None:
        payload = [b.model_dump(mode="json") for b in bookings.values()]
        self._bookings_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._bookings_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._bookings_file)

    def list_bookings(self) -> list[Booking]:
        with _lock:
            return sorted(self._read().values(), key=lambda b: (b.start, b.id))

    def get_booking(self, booking_id: str) -> Optional[Booking]:
        with _lock:
            return self._read().get(booking_id)

    def save(self, booking: Booking) -> None:
        with _lock:
            data = self._read()
            data[booking.id] = booking
            self._write(data)

    def delete(self, booking_id: str) -> bool:
        with _lock:
            data = self._read()
            if booking_id not in data:
                return False
            del data[booking_id]
            self._write(data)
            return True