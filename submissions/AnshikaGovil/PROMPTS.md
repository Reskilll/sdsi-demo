# PROMPTS.md — AI collaboration log

How this submission was built with Claude Code. Each milestone was produced by
a focused prompt; results were reviewed and edge cases added by hand.

## 1. Scope & plan (prompt)
> Act as a Senior Backend developer. Plan a Meeting Room Booking Engine with
> milestones M1–M5 (CRUD, overlap rejection, capacity, find-slot, weekly
> recurrence). Prefer Python + FastAPI + JSON persistence. Keep the plan
> concise.

**Outcome**: chose FastAPI + Pydantic for free validation, half-open intervals
for overlap semantics, JSON store behind a lock.

## 2. Models & validation (prompt)
> Write Pydantic models for Room and Booking with validators enforcing
> start < end, whole-minute alignment, business hours 09:00–18:00, non-empty
> de-duplicated attendees, and a Recurrence with exactly one of count/until.

**Outcome**: `app/models.py`.

## 3. Domain service (prompt)
> Implement overlap detection using half-open intervals, recurrence expansion,
> capacity checks, and a find-slot that scans business hours returning the
> earliest free room and time.

**Outcome**: `app/service.py` (`expand`, `validate`, `find_slot`).

## 4. API + errors (prompt)
> Expose CRUD + find-slot endpoints; return 404 for unknown room/booking,
> 409 with per-occurrence conflict details, 422 via Pydantic.

**Outcome**: `app/main.py`.

## 5. Tests (prompt)
> Write pytest tests covering M1–M5 plus edge cases: back-to-back allowed,
> containment overlap, capacity boundary, recurrence conflicts per occurrence,
> no-slot and invalid params.

**Outcome**: `tests/`.

## Notes on AI collaboration
- JSON file persistence chosen over SQLite for transparency + zero-config run.
- Dependency-injected store/service so tests isolate state in a tmp dir.
- "Back-to-back allowed" was encoded as `a_start < b_end and b_start < a_end`,
  not `<=`, to avoid off-by-one boundary bugs.
