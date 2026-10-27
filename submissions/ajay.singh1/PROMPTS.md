# PROMPTS.md

## Prompt History

### Prompt 1: Project Scaffolding
**Input:** "Build a complete, runnable, well-tested PS2: Meeting Room Booking Engine"

**Approach:**
1. Read the existing repository structure to understand the hackathon format.
2. Identified this is a Python-based submission slot under `submissions/ajay.singh1/`.
3. Chose FastAPI + aiosqlite as the technology stack: FastAPI for its modern async support, aiosqlite for zero-configuration persistence.
4. Designed clean architecture: pure business logic in `engine.py`, framework code in routers, database access isolated in `database.py`.

**Key Design Decisions:**
- **Half-open intervals**: `[start, end)` — a booking ending at 11:00 does not conflict with one starting at 11:00.
- **SQLite WAL + BEGIN IMMEDIATE**: Provides concurrent read access while preventing write race conditions.
- **Deterministic tie-breaking**: Find-slot uses earliest start time, then alphabetical room name.
- **Partial success for recurrence**: Each occurrence independently created/reported — conflicts don't block the series.
- **Pydantic + explicit validation**: Pydantic handles schema, `engine.py` handles business rules.

### Prompt 2: Test Coverage
**Input:** Implicit in "well-tested" requirement

**Approach:**
- Unit tests for `engine.py` — pure functions, easy to test.
- API integration tests via `httpx.ASGITransport` — full HTTP stack, no server needed.
- Concurrency tests using `asyncio.gather` to simulate race conditions.
- Separate test database and rooms file per test run via `tmpdir`.

## Assumptions

1. **Single-day bookings**: Each booking must start and end on the same calendar date.
2. **Reasonable defaults**: Working hours 09:00-18:00, max 52 weekly recurrences.
3. **No timezone handling**: All times are naive datetimes. If timezone-aware timestamps are submitted, timezone info is stripped.
4. **Attendee count** must be a positive integer (max 100,000).
5. **Room names** are case-sensitive and must exactly match `rooms.json`.
6. **Recurrence**: Weekly on the same weekday as the template booking.
7. **Pagination**: Default page size 50, max 100.