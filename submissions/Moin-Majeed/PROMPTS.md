# PROMPTS.md — AI Collaboration Record

## Project: IT Service-Desk SLA Tracker

### Session 1: Initial scaffold and core implementation

**Prompt:**
> I have a problem statement as given below. Create a project for me for the given problem statement in python.
> IT Service-Desk SLA Tracker
> Compute SLA breaches for support tickets...

**AI approach:**

1. **Design phase** — Read the judging criteria (M1–M5), identified the core domain
   objects: `Ticket`, `Priority`, `StatusEntry`, `SlaPolicy`, `TicketReport`,
   `SummaryReport`. Decided on a clean separation: models, business calendar,
   validators, calculator, reporter, CLI.

2. **Architecture decisions:**
   - All datetimes stored as UTC; business calendar converts to local timezone
     internally. This avoids ambiguity around DST transitions.
   - Business calendar operates on calendar-date iteration — walks day-by-day
     counting business minutes. This is simple, correct, and handles all edge
     cases (holidays, weekends, partial days) uniformly.
   - ON_HOLD pause implemented via "active interval" extraction: walk the
     status timeline, open segments at creation/resume and close them at
     ON_HOLD entry or end-of-timeline.
   - Breach is **strictly greater-than** the SLA window (a ticket that takes
     exactly 240 min for a 240-min SLA is not breached).

3. **Implementation order:** models → business_calendar → validators →
   sla_calculator → reporter → cli → sample data → tests → docs.

4. **Sample data design:** 8 tickets covering all scenarios — simple within-SLA,
   ON_HOLD pause, cross-weekend, multiple ON_HOLD segments, created-after-hours,
   still-open, exact-boundary, and short-resolution. All four priorities
   represented.

5. **Testing strategy:**
   - `test_business_calendar.py` — unit tests for the clock (15 tests covering
     within-day, overnight, weekend, holiday, reversed params, negative, etc.).
   - `test_sla_calculator.py` — unit tests for the SLA engine (simple cases,
     ON_HOLD variants, non-business creation, due-by computation, boundary cases).
   - `test_validators.py` — input validation (missing keys, invalid types,
     bad dates, unsorted history).
   - `test_integration.py` — end-to-end tests using the real data files.

### Design rationale — why these choices

**Why not use a library like `businesstimedelta`?**
The business-hours logic is the core of this project and must be auditable.
Writing it from scratch with day-by-day iteration makes the algorithm transparent,
easy to verify, and allows precise handling of edge cases (holiday straddling,
partial-day intervals, status-history pauses).

**Why strict-greater-than for breach?**
Standard SLA interpretation: if the window is 4 hours and it took exactly 4 hours,
you met the SLA. Breach requires exceeding the window.

**Why validators as a separate module?**
Separation of concerns: validation errors catch malformed input before it enters
the domain model. This prevents silent miscalculations and gives clear error
messages to the user. Every JSON loading path goes through a validator first.

**Why frozen dataclasses?**
Immutability prevents accidental mutation of domain objects during computation.
It also makes the data flow explicit — every function returns new objects rather
than modifying state.

### Open questions & future work

- **Timezones with DST**: The business calendar uses `zoneinfo`, which handles
  DST correctly. However, on days where the clock "springs forward" (23-hour day)
  or "falls back" (25-hour day), business minutes per day may differ from 540.
  This is handled correctly by the day-by-day iteration but worth documenting.
- **Multi-tenancy**: Currently one policy, one calendar. Could extend to support
  per-client SLA windows and per-timezone business hours.
- **Streaming**: For very large ticket sets (10M+), could add a streaming reporter
  that yields reports one at a time rather than materializing all at once.
- **Persistence**: Adding a SQLite backend for ticket state would allow
  incremental recomputation rather than full batch runs.