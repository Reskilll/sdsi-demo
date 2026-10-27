import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.service import BookingService
from app.store import Store

ROOMS = [
    {"id": "r1", "name": "Focus Pod", "capacity": 2},
    {"id": "r2", "name": "Huddle", "capacity": 4},
    {"id": "r3", "name": "Boardroom", "capacity": 8},
]


@pytest.fixture()
def client(tmp_path):
    rooms_file = tmp_path / "rooms.json"
    rooms_file.write_text(json.dumps(ROOMS))
    store = Store(rooms_file, tmp_path / "bookings.json")
    app.state.store = store
    app.state.service = BookingService(store)
    with TestClient(app) as c:
        c.store = store
        yield c


def make_booking(room="r1", start="2026-11-02T09:00:00", end="2026-11-02T10:00:00",
                 attendees=("alice@corp.com",), **kw):
    data = {"room_id": room, "organiser": "bob@corp.com", "start": start, "end": end,
            "attendees": list(attendees)}
    data.update(kw)
    return data