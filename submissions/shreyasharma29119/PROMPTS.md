# PROMPTS.md — AI Collaboration Prompts

This file documents the prompts used during development of the SLA Tracker,
along with the rationale and results.

---

## Prompt 1: Project scaffold & architecture

**Prompt:**
> I need to build an IT service-desk SLA tracker in Python. The requirements are:
> M1 — SLA targets by priority (P1=4h, P2=8h, P3=24h, P4=72h), business hours only (Mon–Fri 09:00–18:00).
> M2 — Holidays excluded from SLA time.
> M3 — ON_HOLD status pauses the clock.
> M4 — Per-ticket: elapsed business minutes, due-by, breach yes/no, breach minutes.
> M5 — Summary: breach % per priority and per assignee group.
> Give me a minimal module structure, no external dependencies.

**Result:** Architecture of 6 modules:
- `models.py` (dataclasses)
- `calendar.py` (business-hours math)
- `sla_calculator.py` (active-period extraction + per-ticket result)
- `reporter.py` (table + summary formatting)
- `validation.py` (JSON parsing & input validation)
- `cli.py` (argparse + orchestration)

**Rationale:** Separating the business-hours calendar from the SLA logic from
the reporting makes each module independently testable and reusable.

---

## Prompt 2: Business-hours calendar

**Prompt:**
> Write two functions:
> 1. `business_minutes_between(start, end, holidays)` — counts active minutes
>    between two datetimes, excluding non-business hours, weekends, and holidays.
> 2. `add_business_minutes(start, minutes, holidays)` — projects forward `minutes`
>    business minutes from `start` to produce a due-by datetime.
> Edge cases: start/end outside business hours, spanning weekends/holidays,
> zero minutes, same-day.

**Result:** `calendar.py` with the two functions, handling partial days,
full-day iteration, and holiday exclusions.

**Rationale:** This is the most algorithmically dense part of the tracker.
Getting it right here means the rest of the system is simple.

---

## Prompt 3: ON_HOLD pause logic

**Prompt:**
> Given a ticket with a `status_history` list of `{status, at}` entries,
> extract the time periods where status ≠ ON_HOLD. The clock runs during
> those periods from the last entry to reference_time (or resolved time).

**Result:** `_active_periods()` in `sla_calculator.py` walks the sorted
history and emits (start, end) tuples only for non-ON_HOLD segments.

---

## Prompt 4: Sample data

**Prompt:**
> Create sample JSON data files — 6 tickets exercising all priorities,
> at least one with ON_HOLD pauses, at least one spanning a holiday,
> and one unresolved.

**Result:** `data/tickets.json` with T01–T06 covering:
- T01: P1, same-day resolve, no hold
- T02: P2, two ON_HOLD segments
- T03: P3, unresolved (null)
- T04: P4, multi-day
- T05: P1, spans to next day
- T06: P2, spans a holiday

---

## Prompt 5: Unit tests

**Prompt:**
> Write pytest tests covering M1–M5: business-hours counting (same day,
> crossing boundary, weekend exclusion), holiday exclusion, ON_HOLD pause,
> per-ticket result fields, breach detection, summary computation, and
> input validation.

**Result:** `tests/test_sla.py` with 15+ tests across 7 test classes.

---

## Lessons learned

1. **Business-hours math is subtle** — the edge cases (start before 9am,
   end after 6pm, spanning holidays) needed careful handling. The first
   implementation missed the case where the start datetime is on a non-business
   day; the fix iterates day-by-day.

2. **ON_HOLD segments are directional** — the status at the *start* of each
   history interval determines whether the clock runs for that interval.
   We sort history by `at` before processing.

3. **Input validation matters** — type-checking dates, priorities,
   and status entries at parse time catches errors early rather than
   producing nonsensical SLA results downstream.

4. **Keeping it stdlib-only** avoids version-locking and pip install
   issues, which is valuable for a hackathon submission that evaluators
   need to run without configuration.