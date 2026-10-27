# AI Collaboration Log — PS2 Meeting Room Booking Engine

This file records the prompts, decisions, corrections and verification for the AI-assisted
build. It is deliberately concrete: what was asked, what the model proposed, what was
rejected, and which bugs were found by tests rather than by inspection.

## Tools and working method

- **Agent:** OpenCode coding agent (DeepSeek V4.1 Flash), used interactively.
- **Human direction:** chose the stack (Spring backend, Vue frontend), submission location,
  “no Docker, simple project”, and pushed on recurring-booking edge cases.
- **Workflow:** spec → thin skeleton → domain/service layer → tests → real HTTP smoke test →
  frontend (delegated to a subagent against a frozen API contract) → docs → commits.
- **Guardrails:** every build decision had to be verifiable. Tests are the primary evidence;
  claims in the README were checked with `mvn test`, `mvn package` and `curl` against the
  packaged jar.

## Prompt log (condensed)

### 1. Initial brief

> PS2: Meeting Room Booking Engine — office room-booking backend. M1 CRUD, M2 reject
> overlaps (back-to-back allowed), M3 capacity, M4 find earliest slot 09:00–18:00,
> M5 weekly recurring with conflicts per occurrence. Judged on correctness, design,
> testing, docs, AI collaboration, security, git hygiene, performance, validation.
> Also: java backend and vue frontend. Build under `sdsi-demo/submissions/ritvik.m`.
> Use Spring. No Docker, just a simple project.

**Response/decisions:**

- Spring Boot 3.5.16, Java 21 release target (running on the installed JDK 25), Maven.
- Vue 3 + Vite + TypeScript for the UI; no UI framework.
- H2 file database for zero-setup runs, with Flyway migrations. H2 is the only database
  used (in-memory for tests).
- Explicitly avoided Docker because the environment has none and the brief asked for
  simplicity.

### 2. Architecture prompt

> Design the backend API and persistence for the five requirements, including concurrency
> and time handling. Keep it testable without external services.

**Selected design (after reviewing alternatives):**

| Topic | Choice | Why |
|---|---|---|
| Interval model | Half-open `[start, end)` | Back-to-back bookings need no special case |
| Time representation | Office-local `LocalDateTime` | Single office; avoids offset/DST bugs; documented |
| Conflict prevention | Pessimistic `SELECT … FOR UPDATE` on the room row | Correct under concurrent requests; DB-portable |
| Booking edits | `@Version` optimistic locking | Prevents lost updates across rooms |
| Recurrence | One `BookingSeries` row + one `Booking` row per occurrence | Conflicts are naturally per occurrence; cancellation is ordinary booking state |
| Recurring write mode | Atomic by default, `skipConflicts` opt-in | No half-created series by accident |
| Schema | Flyway V1 + `ddl-auto=validate` | Schema drift fails fast |
| Errors | RFC 9457 problem+json with stable `code` | Machine-readable for the SPA and graders |
| Auth | Stateless HTTP Basic + BCrypt, env-overridable | Real boundary without OAuth setup complexity |

**Rejected:** database exclusion constraints (not portable to H2 and still not a substitute
for application rules), storing only a recurrence rule without materialised occurrences
(makes per-occurrence conflicts and cancellation harder), and a single “magic” endpoint that
guesses between create/update (poor HTTP semantics).

### 3. Recurring-booking edge cases

> Did you handle edge cases? Like rooms being booked during recurring bookings, providing an
> option to book anyway, skipping the booked room, etc.

**Implemented/verified:**

- **Preview then create:** `POST /api/bookings/recurring/preview` reports `FREE`/`CONFLICT`
  per occurrence with the clashing bookings. It writes nothing.
- **Race safety:** create ignores the preview result, locks the room, and re-runs conflict
  detection across the whole series before inserting. A booking made between preview and
  create is caught.
- **Atomic default:** any conflict returns `409 RECURRING_CONFLICT`, lists only conflicting
  occurrences, and creates **zero** rows/series.
- **Book the rest anyway:** `skipConflicts: true` creates the free occurrences and returns
  them in `created[]`, with conflicting ones in `skipped[]` plus a “Created X of Y” message.
- **All conflict:** even with `skipConflicts`, the API returns `409` rather than an empty
  series.
- **Other recurrence edges tested:** multiple weekdays, default weekday, mid-week start,
  week window based on the Monday of `startsOn`, no-occurrence windows, duplicate days,
  52-week/366-occurrence cap, year boundary, cancel-future-only, series inspection.

### 4. Frontend delegation

> Can you let a subagent work in parallel for the frontend part?

**Approach:** froze the HTTP contract in [`API.md`](API.md) first (endpoints, payloads,
status codes, auth, wall-clock time rule), then gave a subagent a self-contained brief:
Vue 3 + TS + Vite, no UI library, login via Basic auth in `sessionStorage`, three views
(day timeline, find-slot, recurring preview/create), typed API/error client, Vitest tests,
and mandatory `npm run build` + `npm test`. The backend was declared off-limits to the
subagent to avoid overlapping edits.

### 5. Duplicate bookings

> Ensure that duplicate bookings aren’t allowed and other such test cases shouldn’t be failing.

**Response:** an exact duplicate is just the degenerate overlap case, so it is rejected by
the same check. Added an explicit regression test (`exactDuplicateBookingIsRejected`) plus
concurrent-create tests: four simultaneous requests for the same room/slot yield exactly one
`201` and three `409`s. Conflict tests cover partial overlap, containment in both
directions, same time in different rooms, and update-into-overlap.

### 6. “Move faster”

Trade-off made: keep the already-designed scope, stop adding speculative features, and
prioritise green tests, the real HTTP smoke test, documentation, and commits. The remaining
nice-to-have (automatic relocation of conflicting recurrence occurrences to another room)
was left out rather than shipped untested; skip-conflicts plus per-occurrence conflict
details and `find-slot` alternatives cover the stated need.

## Bugs found during verification (and fixes)

1. **Custom problem+json advice was bypassed.** Spring Boot’s own
   `ProblemDetailsExceptionHandler` handled MVC exceptions first, so responses lacked the
   project’s `code`/`errors`/`conflicts` fields.
   → Annotated `ApiExceptionHandler` with `@Order(HIGHEST_PRECEDENCE)`; structured errors
   now win (regression tests assert `code` and `errors`).

2. **401 responses had no `WWW-Authenticate` header.** Replacing the default entry point to
   return problem+json dropped the Basic challenge.
   → Added `WWW-Authenticate: Basic realm="room-booking"` to the custom entry point;
   `ValidationAndSecurityTest` asserts it.

3. **Created bookings returned without `createdAt`/`updatedAt`.** Spring Data treats a
   UUID-assigned new entity as possibly detached and may return a merged copy; the service
   mapped the original instance. The database had values, so list/get looked fine.
   → Set audit timestamps in the entity constructor and map the entity returned by
   `saveAndFlush`. A regression assertion now checks both fields on create.

4. **Second-level timestamps bypassed the 15-minute grid.** `09:00:30` produced a
   non-grid find-slot candidate after `Duration.toMinutes()` truncation.
   → Reject non-whole-minute booking times (`INVALID_INTERVAL`) and tested it.

5. **Test expectation bug, not an API bug:** `LocalDateTime.toString()` omits `:00`
   seconds while Jackson serialises them; recurring assertions used the wrong expected
   string. → Standardised test formatting on `yyyy-MM-dd'T'HH:mm:ss`.

6. **False alarm during smoke testing:** `curl -d '<json with a space>'` in PowerShell
   split the argument, producing `INVALID_JSON`. → Re-ran with `--data-binary @file.json`;
   create returned `201`. The API had behaved correctly.

## Deliberate AI-output reviews

- Removed a custom `currentOfficeDate` helper that was dead code.
- Replaced duplicated free-window arithmetic with a pure `FreeWindows` utility so the
  touching/overlap/clipping cases are unit-testable without Spring.
- Kept capacity rejection at **400** (invalid request against a known constraint) and
  overlap at **409** (conflict with current state), then documented the distinction so a
  grader is not surprised.
- Rejected cleartext/hardcoded credentials in source; credentials are properties/env with
  BCrypt at startup and a warning when the demo default is used.
- Rejected disabling CSRF without setting stateless sessions; both are configured together.
- Added an API-body size limit after noting that Bean Validation runs only after buffering.

## Verification evidence

```text
mvn test      → 81 tests, 0 failures, 0 errors (11 test classes)
mvn package   → target/room-booking-1.0.0.jar
curl smoke    → rooms 200, create 201, duplicate/overlap 409 (conflicts[] populated),
                back-to-back 201, find-slot 200 with slot+alternatives, no-auth 401,
                /v3/api-docs 200
```

Commands and run instructions are in [`README.md`](README.md); the evaluator-facing HTTP
contract is in [`API.md`](API.md).
