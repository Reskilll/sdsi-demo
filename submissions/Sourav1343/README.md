# Meeting Room Booking Engine -- PS2

## Problem

Build an office room-booking backend that supports CRUD operations on
bookings, rejects overlapping bookings for the same room (while allowing
back-to-back), enforces room-capacity constraints, finds the earliest
available slot across all rooms, and handles weekly recurring bookings with
per-occurrence conflict reporting.

## Solution Architecture

```
submissions/Sourav1343/
├── engine/                        # Core library (zero-dependency Python 3.10+)
│   ├── __init__.py               # BookingEngine -- public API
│   ├── models.py                 # Dataclasses: Room, Booking, BookingRequest, etc.
│   ├── store.py                  # Thread-safe in-memory store + JSON persistence
│   ├── validator.py              # Input validation & overlap checks
│   ├── recurrence.py             # Weekly recurrence expansion
│   └── finder.py                 # Find-slot algorithm (09:00-18:00)
├── tests/                         # Pytest suite
│   ├── conftest.py               # Sets up PYTHONPATH
│   ├── test_models.py            # Validation & models (M1 edge cases)
│   ├── test_overlap.py           # Overlap rules (M2)
│   ├── test_find_slot.py         # Find-slot algorithm (M4)
│   ├── test_recurrence.py        # Weekly recurrence (M5)
│   ├── test_validation.py        # Adversarial edge cases
│   └── test_engine.py            # CRUD lifecycle (M1, M3) + persistence
├── agent.py                       # Scaffold-compatible CLI wrapper
├── rooms.json                     # Sample room catalogue (M3)
├── run_demo.py                    # End-to-end demo script
├── requirements.txt              # pytest>=8.0
├── pytest.ini
├── .gitignore
├── README.md
└── PROMPTS.md
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No database** | In-memory store with JSON file persistence. Zero external deps. |
| **No web framework** | CLI first via `run_demo.py`. Engine is importable as a library. |
| **Pure Python stdlib core** | `pytest` is the only optional dep (for testing). |
| **Half-open intervals** | `a_start < b_end AND b_start < a_end` -- back-to-back allowed. |
| **Recurrence stored as template** | Expanded on conflict check and slot search. |

## Setup

```bash
cd submissions/Sourav1343

# Install test-only dependency (optional)
pip install -r requirements.txt

# Run the demo
python run_demo.py

# Run tests
python -m pytest tests/ -v
```

## API Reference

### `BookingEngine(rooms_file, data_file=None)`

All operations go through the engine:

```python
from engine import BookingEngine
from engine.models import BookingRequest

engine = BookingEngine("rooms.json")

# M1: CRUD
result = engine.create_booking(BookingRequest(
    id="b1", room_id="r1", organiser="alice",
    start_time="2026-10-27T09:00", end_time="2026-10-27T10:00",
    attendees=["bob"],
))
booking = engine.read_booking("b1")
result = engine.update_booking(...)  # replace entire booking
engine.delete_booking("b1")

# M4: find-slot
slot = engine.find_slot(60, 3, "2026-10-27")  # 60 min, 3 people

# Utility
engine.list_rooms()
engine.list_bookings(room_id="r1", date_str="2026-10-27")
engine.save()
```

### `agent.run(task: str) -> dict`

Scaffold-compatible wrapper for JSON commands:

```bash
python agent.py '{"action":"create","booking":{...}}'
python agent.py '{"action":"list-rooms"}'
python agent.py '{"action":"find-slot","duration_minutes":60,"attendee_count":3,"date":"2026-10-27"}'
```

### `BookingResult`

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | `True` if the booking was applied |
| `booking` | `Booking \| None` | The created/updated booking |
| `conflicts` | `list[Conflict]` | Per-occurrence overlap reasons (M5) |
| `errors` | `list[str]` | Validation error messages |

### `Slot`

| Field | Type | Description |
|-------|------|-------------|
| `room` | `Room` | The room with sufficient capacity |
| `start` | `datetime` | Earliest free start time |
| `end` | `datetime` | `start + duration` |

## Requirements Mapping (M1-M5)

| Req | Description | Coverage |
|-----|-------------|----------|
| M1 | CRUD for bookings | `BookingEngine.create/read/update/delete_booking` |
| M2 | Overlap rejection + back-to-back | Half-open interval check in `validator.overlaps()` |
| M3 | Capacity validation + rooms.json | `check_capacity()`, sample file included |
| M4 | Find-slot (09:00-18:00) | `find_available_slot()` -- globally earliest, deterministic |
| M5 | Weekly recurrence + per-occurrence conflicts | `expand_occurrences()`, `assert_no_overlaps()` expands both sides |

## Assumptions & Limitations

1. **Naive datetimes only** -- timezone-aware ISO strings are explicitly
   rejected. The engine uses naive local datetimes throughout.
2. **Recurrence format** -- weekly from `start_time`, 7-day calendar steps,
   inclusive of `recurrence_weekly_until`. The `until` date does not need to
   match the start weekday; the last occurrence is the one on or before
   `until` on the same weekday.
3. **Recurring bookings must not span midnight** -- each occurrence must
   have `start_time` and `end_time` on the same calendar date for a clear
   weekday anchor. One-off bookings may span midnight.
4. **Find-slot business hours** -- 09:00-18:00 inclusive for the booking
   interval. A booking may *end* exactly at 18:00, but may not extend beyond.
5. **Persistence** -- atomic file replacement (write temp, rename). Not
   designed for multi-process access; the lock only protects a single engine
   instance.
6. **Booking IDs are client-generated** -- the engine validates uniqueness.
7. **Organiser is metadata** -- the `organiser` field is not counted in
   capacity checks. Only `attendees` count toward capacity.

## Running the Demo

```
python run_demo.py
```

Expected output demonstrates all M1-M5 requirements with labeled [OK]
successes and [XX] rejections.

## Running Tests

```
python -m pytest tests/ -v    # 91 tests
```