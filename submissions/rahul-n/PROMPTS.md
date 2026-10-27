# PROMPTS.md — build context

## Original brief

> Act as a Staff Backend Engineer. Build a high-quality, production-ready "Meeting Room
> Booking Engine" using Java 21, Spring Boot 3.x, and an H2 In-Memory Database.
>
> - **Data:** Spring Data JPA + H2, seed ≥3 distinct rooms (Room A cap 5, Room B cap 10,
>   Room C cap 20).
> - **Concurrency:** `@Lock(LockModeType.PESSIMISTIC_WRITE)` on the room repository during
>   transaction boundaries to eliminate double-booking races.
> - **Time:** `OffsetDateTime`/`Instant` throughout for timezone resilience.
> - **M1 CRUD:** bookings with id, roomId, organiser, startTime, endTime, attendees.
> - **M2 Overlap:** reject overlapping bookings; back-to-back must be allowed.
> - **M3 Capacity:** `attendees.size() <= room.capacity`, else 400 with a clear message.
> - **M4 Find-slot:** `GET /api/bookings/find-slot?duration=60&attendeeCount=8&date=…`
>   returns the earliest window strictly between 09:00 and 18:00, preferring the
>   **smallest compliant room** so large rooms stay free.
> - **M5 Recurrence:** two-step dry-run/confirm for weekly bookings — step 1 validates all
>   occurrences and reports which dates are available or blocked, plus a token/payload for
>   step 2, which saves *only* the available slots.
> - **Stretch:** `/api/analytics/utilization` percentage per room over a week.

## Follow-up audit prompt

> 1. Time boundary checks — a 60-minute slot at 17:00 is valid; one at 17:30 must not be offered.
> 2. Timezone integrity — compare absolute instants so differing client offsets cannot bypass overlap.
> 3. Empty/null/malformed inputs — `@NotNull`, `@Size`, `@FutureOrPresent` on DTOs, handled cleanly.
> 4. Duplicate attendees — reject if the same attendee appears twice.

## Engineering decisions

| Decision | Rationale |
|---|---|
| Half-open interval `[start, end)` | Makes back-to-back bookings legal by construction — a single `<`/`>` predicate handles M2 and the touching-boundary case with no special-casing. |
| Pessimistic write lock on `Room` | Serialises check-and-insert per room. Locking the *room* rather than the booking row means a first-ever booking for a room is protected too, where an optimistic retry loop would spin. |
| UTC-normalised `OffsetDateTime` | Both storage and comparison in UTC. Storing the client's offset would let `09:00Z` and `14:30+05:30` — the same instant — coexist in a unique index. |
| 09:00–18:00 UTC, weekdays | The brief's window needs a concrete interpretation; fixing it to UTC keeps "09:00" unambiguous and DST-proof, and makes the utilization denominator well-defined. |
| Best-fit = smallest capacity first | Directly satisfies M4's stated optimisation; ordering lives in one repository method so it cannot drift. |
| Sweep jumps past conflicts | The find-slot scan advances to the end of each conflicting booking rather than stepping minute-by-minute, so an occupied day costs O(bookings) not O(minutes). |
| HMAC-signed plan token | Keeps M5's two-step flow stateless — the server trusts the roster of vetted slots on the confirm call without holding session state — while still rejecting tampered or expired plans. |
| Empty `occurrences` ≠ absent | Absent commits the whole plan; an explicit empty list commits nothing. Lets a client decline a plan without discarding a valid token, and keeps the two intents distinguishable. |
| Duplicate check before capacity check | A repeated attendee would otherwise inflate the count against room capacity, producing a misleading "capacity exceeded" error for what is really a malformed input. |
| `AttendeeRules` shared by both write paths | CRUD and recurrence reject identical inputs with identical messages; bean validation alone would not cover programmatic callers, so the service layer enforces it too. |

## Deliberate scope limits

- No authentication or per-user authorization — attendees are opaque identity strings.
- Bookings outside 09:00–18:00 UTC weekdays are rejected outright rather than supported as
  a separate mode.
- Recurrence is fixed weekly (`plusWeeks`), not RRULE/CRON.
- `find-slot` scans a single day; multi-day search would extend the same sweep.
- H2 in-memory: state resets per boot, which is the brief's intent.

## Verification

`mvn test` → **66 tests, 0 failures**. Coverage is organised by concern: M1 CRUD, M2 overlap
(incl. touching boundaries), M3 capacity, M4 best-fit and window edges, M5 dry-run/commit
(incl. subset selection and tampered tokens), analytics, plus four audit suites (time
boundaries, timezone integrity, malformed input, duplicate attendees) and
`BookingConcurrencyIntegrationTest`, which asserts exactly one winner across 12 simultaneous
identical requests and zero overlapping pairs across 24 randomised concurrent requests.
