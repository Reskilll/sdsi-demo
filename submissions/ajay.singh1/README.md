# Meeting Room Booking Engine

**PS2: Meeting Room Booking Engine — SDSI Agentic AI Hackathon**

A complete REST API for managing meeting room bookings with conflict prevention,
room capacity validation, find-slot optimization, and weekly recurrence support.

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --port 8000
```

The server starts at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `bookings.db` | SQLite database path |
| `ROOMS_PATH` | `rooms.json` | Room definitions |
| `MAX_RECURRENCE_OCCURRENCES` | `52` | Max weekly occurrences |
| `WORKING_HOURS_START` | `9` | Working hours start (24h) |
| `WORKING_HOURS_END` | `18` | Working hours end (24h) |

## API Reference

### Health Check
```
GET /health → 200 { "status": "ok" }
```

### Rooms
```
GET /rooms → 200 [{ "name": "Alpha", "capacity": 4 }, ...]
```

### Bookings (CRUD)

**Create booking**
```
POST /bookings
Body: { "room": "Gamma", "organiser": "Alice",
        "start_time": "2026-12-01T10:00:00",
        "end_time": "2026-12-01T11:00:00",
        "attendee_count": 4 }
→ 201 { "id": 1, ... }
```

**List bookings** (with pagination and filters)
```
GET /bookings?page=1&page_size=50&room=Gamma&date_from=2026-12-01&date_to=2026-12-31
→ 200 { "bookings": [...], "total": N, "page": 1, "page_size": 50 }
```

**Get booking**
```
GET /bookings/{id} → 200 { ... }
```

**Update booking**
```
PUT /bookings/{id}
Body: { "organiser": "Bob" }
→ 200 { ... }
```

**Delete booking**
```
DELETE /bookings/{id} → 204
```

### Find Slot
```
POST /find-slot
Body: { "date": "2026-12-01", "duration_minutes": 60, "attendee_count": 4 }
→ 200 { "available": true, "room": "Alpha",
        "start_time": "2026-12-01T09:00:00",
        "end_time": "2026-12-01T10:00:00" }
```

### Weekly Recurrence
```
POST /bookings/recurring
Body: {
  "room": "Gamma", "organiser": "Alice",
  "start_time": "2026-12-01T10:00:00",
  "end_time": "2026-12-01T11:00:00",
  "attendee_count": 4,
  "recurrence_start": "2026-12-01",
  "recurrence_end": "2026-12-29"
}
→ 201 {
  "created": [{ "date": "2026-12-01", "booking": { ... } }, ...],
  "conflicts": [{ "date": "2026-12-08", "conflict": { ... } }],
  "failures": []
}
```

## Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad request (validation error) |
| 404 | Not found |
| 409 | Conflict (overlapping booking) |
| 422 | Unprocessable (invalid schema) |
| 500 | Internal server error |

## Architecture

```
app/
├── main.py          # FastAPI app, lifespan, error handlers
├── config.py        # Environment-based configuration
├── models.py        # Pydantic request/response schemas
├── database.py      # SQLite async access, init, conflict checks
├── rooms.py         # Room loading from JSON
├── engine.py        # Pure business logic (no I/O)
└── routers/
    ├── bookings.py  # CRUD endpoints
    ├── rooms.py     # Room listing
    ├── find_slot.py # Find-slot endpoint
    └── recurrence.py # Recurring booking endpoint

tests/
├── conftest.py          # Fixtures
├── test_engine.py       # Unit tests (business logic)
├── test_api.py          # Integration/API tests
└── test_concurrency.py  # Race condition tests
```

### Design Decisions

- **Clean architecture**: Business logic in `engine.py` is pure functions with no I/O or framework dependencies.
- **Half-open intervals**: Bookings use `[start, end)` — a booking ending at 11:00 does not block another starting at 11:00.
- **Concurrency**: SQLite `BEGIN IMMEDIATE` transactions prevent race conditions.
- **Validation**: Pydantic for request schemas, plus business validation in `engine.py`.
- **Tie-breaking**: Find-slot returns the earliest start time; alphabetically first room name on ties.

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_engine.py -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=app -v
```

## Known Limitations

1. **SQLite**: Uses file-based SQLite. For production, migrate to PostgreSQL with connection pooling.
2. **No authentication**: API is open. Add authentication middleware for production.
3. **DST edge cases**: During DST "spring forward" gaps (e.g., 02:00→03:00), time slots in the gap are silently advanced.
4. **No multi-tenancy**: Single organisation. Add tenant IDs for multi-organisation support.
5. **Recurrence**: Weekly only. No bi-weekly, monthly, or custom RRULE support.

## Requirement-to-Test Checklist

| Requirement | Test | Status |
|---|---|---|
| M1: Create booking | `test_create_valid_booking` | ✅ |
| M1: Read booking | `test_get_existing` | ✅ |
| M1: List bookings | `test_list_with_bookings` | ✅ |
| M1: Update booking | `test_update_room` | ✅ |
| M1: Delete booking | `test_delete_existing` | ✅ |
| M1: Invalid input | `test_missing_required_field`, `test_invalid_date_format` | ✅ |
| M2: Exact overlap rejected | `test_exact_overlap_rejected` | ✅ |
| M2: Partial overlap rejected | `test_partial_overlap_start`, `_end` | ✅ |
| M2: Back-to-back allowed | `test_back_to_back_allowed` | ✅ |
| M2: Different rooms OK | `test_different_rooms_no_conflict` | ✅ |
| M2: Concurrency | `test_concurrent_same_slot` | ✅ |
| M3: Room list | `test_rooms_list` | ✅ |
| M3: Capacity validation | `test_capacity_exceeded` | ✅ |
| M3: Room existence | `test_room_not_found` | ✅ |
| M4: Find empty slot | `test_basic_find` | ✅ |
| M4: No room available | `test_no_available_room` | ✅ |
| M4: With existing bookings | `test_with_existing_bookings` | ✅ |
| M4: Tie-breaking | `test_deterministic_tie_breaking` | ✅ |
| M5: Weekly recurrence | `test_basic_recurrence` | ✅ |
| M5: Recurrence with conflicts | `test_recurrence_with_conflict` | ✅ |
| M5: Recurrence failure handling | `test_recurrence_capacity_failure` | ✅ |
| Boundary: Zero attendee | Pydantic gt=0 | ✅ |
| Boundary: Max capacity | `test_capacity_exact` | ✅ |
| Boundary: Empty schedule | `test_empty_schedule_returns_9am` | ✅ |