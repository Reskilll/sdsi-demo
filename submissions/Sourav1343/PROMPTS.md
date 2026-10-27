# PROMPTS.md — AI Collaboration Record

This file records the key prompts exchanged with Claude Code during
development of the Meeting Room Booking Engine (PS2) for SDSI Digithon 2026.

---

## Prompt 1: Initial Instructions (Phase 1-5)

The user provided a comprehensive 5-phase instruction set for building the
hackathon solution. Key directives:

- Inspect the repository before coding.
- Plan the solution before implementing.
- Build inside `submissions/Sourav1343/` only.
- Use Python, stay compatible with `agent-template/agent.py`.
- Zero external dependencies unless justified.
- Include tests, README, PROMPTS.md, runnable demo.

**Decision:** The plan was built around a pure-stdlib engine core with
pytest as the only optional dependency. Dataclasses for models, in-memory
store with thread-lock, and CLI-first interface.

---

## Prompt 2: Problem Statement Assignment

The user confirmed the assigned use case:

> **PS2: Meeting Room Booking Engine** — Build an office room-booking
> backend with CRUD (M1), overlap rejection (M2), capacity validation (M3),
> find-slot algorithm (M4), and weekly recurrence with conflict reporting
> (M5).

**Decision:** Mapped each requirement to a specific module and test file.
Designed half-open interval overlap rule (`a_start < b_end and b_start < a_end`).

---

## Prompt 3: Phase 2 Plan Approval with Clarifications

The user approved the plan with 10 detailed clarifications covering:
scope compatibility, overlap rules, recurrence semantics, find-slot
correctness, timezone handling, update rollback, input validation,
testing matrix, documentation, and delivery expectations.

**Decisions made from clarifications:**
- Timezone-aware datetimes are explicitly rejected rather than silently
  converted to naive.
- Recurrence expansion is inclusive of `recurrence_weekly_until`.
- Update excludes the booking being replaced from conflict checks.
- Find-slot returns the globally earliest slot with room-ID tiebreaking.
- Concurrent create access tested with shared-engine multi-thread test.

---

## Prompt 4: Implementation & Iterative Debugging

During implementation, issues discovered and fixed:

1. **Validator parameter mismatch** — `validate_booking_request` expected
   `dict[str, Room]` but the engine passed `set[str]` (room ids). Fixed by
   adding `list_room_map()` to the store and updating engine calls.

2. **Recurring existing bookings not expanded** — `assert_no_overlaps`
   compared candidate occurrences against stored templates without
   expanding recurring existing bookings. Fixed by using `expand_to_date`
   on each existing booking during conflict checks.

3. **Unicode encoding on Windows** — demo output used em-dashes and Unicode
   checkmarks that caused `UnicodeEncodeError` with CP1252 terminal. Fixed
   by converting all user-facing output to ASCII.

4. **Test data causing false positives** — `test_recurrence_atomic_rejection`
   had back-to-back intervals (blocker at 10:00-11:00, candidate occurrence
   at 09:30-10:00) that should have been allowed. Fixed the test data to
   create a genuine overlap.

---

## Final Results

- **91 tests pass** across 6 test files covering M1-M5 plus edge cases.
- **End-to-end demo runs** cleanly, demonstrating all mandatory requirements.
- No external runtime dependencies beyond Python 3.10 standard library.