"""Test fixtures and configuration."""
import os
import sys
import json
import tempfile
import pytest
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMPDIR = None


def _setup_env():
    """One-time env setup per test function."""
    global _TMPDIR
    from app import config, rooms
    rooms._rooms.clear()

    # Clean up any prior tmpdir
    if _TMPDIR and os.path.isdir(_TMPDIR):
        shutil.rmtree(_TMPDIR, ignore_errors=True)

    _TMPDIR = tempfile.mkdtemp()
    db_path = os.path.join(_TMPDIR, "test_bookings.db")
    rooms_path = os.path.join(_TMPDIR, "test_rooms.json")

    os.environ["DATABASE_PATH"] = db_path
    os.environ["ROOMS_PATH"] = rooms_path
    config.DATABASE_PATH = db_path
    config.ROOMS_PATH = rooms_path

    with open(rooms_path, "w") as f:
        json.dump([
            {"name": "Alpha", "capacity": 4},
            {"name": "Beta", "capacity": 6},
            {"name": "Gamma", "capacity": 8},
            {"name": "Delta", "capacity": 12},
            {"name": "Epsilon", "capacity": 20},
        ], f)


@pytest.fixture
async def client():
    """Fresh app + fresh DB per test."""
    _setup_env()

    from app.database import init_db
    from app.rooms import load_rooms
    await init_db()
    load_rooms()

    from fastapi import FastAPI
    from app.routers import bookings, room_list, find_slot, recurrence
    app = FastAPI()
    app.include_router(bookings.router)
    app.include_router(room_list.router)
    app.include_router(find_slot.router)
    app.include_router(recurrence.router)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_booking(client):
    """Create a sample booking and return its response JSON."""
    resp = await client.post("/bookings", json={
        "room": "Gamma",
        "organiser": "Alice",
        "start_time": "2026-12-01T10:00:00",
        "end_time": "2026-12-01T11:00:00",
        "attendee_count": 4,
    })
    assert resp.status_code == 201, f"Fixture failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.fixture(scope="function")
def setup_test_env():
    """Synchronous fixture for unit tests that only need rooms loaded."""
    _setup_env()
    from app.rooms import load_rooms
    load_rooms()
    yield