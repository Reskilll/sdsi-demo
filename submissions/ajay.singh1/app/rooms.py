import json
from pathlib import Path
from .models import RoomResponse


_rooms: dict[str, RoomResponse] = {}


def _rooms_path() -> str:
    import app.config
    return app.config.ROOMS_PATH


def load_rooms(path: str | None = None) -> dict[str, RoomResponse]:
    """Load rooms from a JSON file. Returns dict keyed by room name."""
    global _rooms
    filepath = Path(path or _rooms_path())
    if not filepath.exists():
        raise FileNotFoundError(f"Rooms file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    _rooms.clear()
    for entry in raw:
        room = RoomResponse(**entry)
        _rooms[room.name] = room
    return dict(_rooms)


def get_rooms() -> dict[str, RoomResponse]:
    """Return currently loaded rooms."""
    if not _rooms:
        load_rooms()
    return dict(_rooms)


def room_exists(name: str) -> bool:
    return name in get_rooms()


def room_capacity(name: str) -> int:
    rooms = get_rooms()
    if name not in rooms:
        raise KeyError(f"Room '{name}' not found")
    return rooms[name].capacity