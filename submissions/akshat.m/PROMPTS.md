# AI Collaboration — Meeting Room Booking Engine

This document describes how an AI assistant (Claude Code) built this project
and how to effectively collaborate with it on similar tasks.

## How it was built

### 1. Understand → Plan → Build (3 cycles)

The assistant was given a problem statement with milestones M1–M5 and asked to
produce a working solution in under 30 minutes.

**Cycle 1 — Scaffold**: Parse the spec, choose a zero-dependency tech stack
(pure Node.js/TypeScript with file-based JSON storage), create project
structure (`data/`, `src/`, `package.json`).

**Cycle 2 — Implement**: Write the three core files in dependency order:
1. `src/db.js`       — file I/O abstraction
2. `src/services.js`  — business logic (CRUD, overlap detection, capacity
   validation, slot-finder algorithm, weekly recurring expansion)
3. `src/server.js`    — HTTP server using Node's built-in `http` module with
   URL-based routing

**Cycle 3 — Test & Fix**: Run the test suite, fix timezone issues (all times
in UTC), fix the `dateRange` comparison in recurring bookings, correct
`findSlot` room-sorting, and verify all M1–M5 endpoints via curl.

### Key design decisions

| Decision | Rationale |
|---|---|
| Zero dependencies | Runs without `npm install`; judged on runnability |
| JSON file storage | Simple, inspectable, works for the dataset size |
| UTC everywhere | Avoids timezone ambiguities in slot-finding |
| Service layer | Separates HTTP from business logic for testability |
| 30-min slot granularity | Matches typical meeting patterns; simple to implement |
| `overlaps()` with strict `<` | Allows back-to-back (end == start) by design |

### Prompts used

1. **Problem understanding** — "Create a plan for this problem statement..."
   (no plan file was actually written; the assistant built directly after
   a mental plan).

2. **Scaffold** — Created `package.json`, `data/rooms.json`, 3 source files.

3. **Iterate** — Ran tests, fixed bugs, added edge-case handling.

### Tips for AI collaboration on this kind of task

- Give milestones (M1–M5) explicitly — they map to test cases and the
  evaluation rubric.
- For time-bounded tasks (<30 min), avoid over-engineering. A flat service
  file with clear functions beats deep class hierarchies.
- When tests fail, read the actual vs expected output carefully — timezone
  and ordering assumptions are the most common false positives.
- Use `node --test` for fast iteration without external test runners.
- Ask the AI to run a curl-based smoke test in addition to unit tests to
  validate the HTTP layer works end-to-end.
- For the overlap check, confirm the spec says "back-to-back allowed" —
  this means `<` not `<=` in the comparison.
- For `findSlot`, the algorithm choice (room-first vs time-first) affects
  which room is returned for tied start times. Sorting rooms by capacity
  (ascending) and picking the first free slot gives predictable results.
- Recurring booking expansion must normalise dates to UTC midnight before
  comparing — an ISO timestamp with a time component shifts the comparison
  against the bare `recurrenceEnd` date.