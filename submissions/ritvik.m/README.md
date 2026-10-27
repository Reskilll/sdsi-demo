# Meeting Room Booking Engine — PS2

A full-stack office room-booking service: **Spring Boot 3.5 / Java 21 backend** and a
**Vue 3 + TypeScript frontend**. It implements all five judged behaviours (CRUD, overlap
prevention, capacity checks, earliest-slot search, weekly recurrence with per-occurrence
conflicts) plus a set of robustness and DX extras.

```
submissions/ritvik.m/
├── API.md                 # detailed HTTP contract for the frontend/evaluator
├── PROMPTS.md             # AI collaboration log, decisions and corrections
├── backend/               # Spring Boot API, Flyway schema, tests
└── frontend/              # Vue 3 SPA (Vite + TypeScript + Vitest)
```

---

## Run it

Prerequisites: **JDK 21+**, **Maven 3.9+**, **Node 20+**. No Docker and no external
database are needed.

Run the backend in one terminal:

```bash
cd submissions/ritvik.m/backend
mvn spring-boot:run
```

Wait for `Started BookingApplication` and check <http://localhost:8080/actuator/health>.

Run the frontend in a second terminal:

```bash
cd submissions/ritvik.m/frontend
npm install
npm run dev
```

Open **<http://localhost:5173>** and sign in with **`admin` / `admin123`**.

The Vite dev server proxies `/api` to `http://localhost:8080`, so both processes must be
running. The backend creates its H2 database in `backend/data/` on first start and seeds
the six demo rooms automatically.

### Single-jar option (no Node at runtime)

Building with the `frontend` profile compiles the SPA and copies it into the Spring Boot
static resources, so one process serves both the UI and the API:

```bash
cd submissions/ritvik.m/backend
mvn -Pfrontend package
java -jar target/room-booking-1.0.0.jar
```

Open <http://localhost:8080> (same credentials).

### Troubleshooting

- **Port 5173 already in use:** stop the other process, or run `npm run dev -- --port 5175`
  and open the port Vite prints. Always use the exact URL from the Vite banner.
- **`/api` calls fail in the browser:** confirm the backend is on port 8080; the proxy
  target is set in `frontend/vite.config.ts`.
- **Reset the demo data:** stop the backend and delete `backend/data/`.
- **Change credentials:** set `APP_ADMIN_USERNAME` / `APP_ADMIN_PASSWORD` before starting
  the backend.

## Quick start

Prerequisites: **JDK 21+**, **Maven 3.9+**, **Node 20+** (built and tested with JDK 25,
Maven 3.10, Node 22). No Docker or external database is needed.

### 1. Backend (port 8080)

```bash
cd backend
mvn spring-boot:run
```

- H2 file database: `backend/data/booking.mv.db` (created on first run, delete to reset).
- Rooms are seeded from `backend/src/main/resources/rooms.json` on first start.
- Swagger UI: <http://localhost:8080/swagger-ui.html> · OpenAPI JSON: `/v3/api-docs`
- Health: <http://localhost:8080/actuator/health>
- Demo credentials: **admin / admin123** (HTTP Basic). Override before exposing the service:

```bash
APP_ADMIN_USERNAME=me APP_ADMIN_PASSWORD='a-long-secret' mvn spring-boot:run
```

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> and sign in with `admin` / `admin123`. Vite proxies `/api`
to `http://localhost:8080`, so no CORS setup is needed in development.

### 3. Tests / build

```bash
cd backend
mvn test          # 81 unit + integration tests, random-free, isolated H2 database
mvn verify        # tests + JaCoCo report at target/site/jacoco/index.html
mvn package       # runnable jar at target/room-booking-1.0.0.jar
```

Single-jar deployment (builds the SPA, copies `dist` into Spring static resources):

```bash
cd backend
mvn -Pfrontend package
java -jar target/room-booking-1.0.0.jar
```

Frontend checks:

```bash
cd frontend
npm run build     # vue-tsc type-check + Vite production build
npm test          # Vitest unit tests
```

### PostgreSQL instead of H2

The schema is portable and managed by Flyway; the driver is already on the classpath.

```bash
DB_URL='jdbc:postgresql://localhost:5432/booking' \
DB_USERNAME=booking DB_PASSWORD=secret \
mvn spring-boot:run
```

---

## Requirements coverage

| ID | Requirement | Implementation |
|---|---|---|
| **M1** | Create, read, update, delete bookings (room, organiser, start, end, attendees) | `/api/bookings` CRUD, full/partial attendee input, cancel vs hard delete, filters + pagination, ICS export |
| **M2** | Reject overlaps; back-to-back allowed | Half-open interval check `existing.start < new.end && existing.end > new.start`; overlaps return `409 BOOKING_CONFLICT` with conflict details. Cancelled bookings do not block. Exact duplicates, containment and partial overlaps are all rejected. |
| **M3** | Reject attendee count above room capacity | Capacity from seeded `rooms.json` (2–24); effective headcount from `attendeeCount` and/or `attendees` (must agree); `400 CAPACITY_EXCEEDED` |
| **M4** | Earliest free room/time for duration + date, 09:00–18:00 | `GET /api/find-slot` (alias `/api/slots`): 15-minute grid, capacity/amenity/room filters, business-hours clipping, today-aware, returns best slot + alternatives |
| **M5** | Weekly recurrence with conflicts per occurrence | `POST /api/bookings/recurring` + `/preview`: weekday set over N weeks, per-occurrence FREE/CONFLICT report, atomic-by-default, opt-in `skipConflicts` |

### Behaviour details that matter

- **Overlap under concurrency:** booking writes take a `SELECT … FOR UPDATE` lock on the
  room row, then check overlaps and insert in the same transaction. Four simultaneous
  requests for one slot produce exactly one booking (covered by `ConcurrencyTest`).
- **Recurring conflicts are re-checked at write time**, not trusted from a preview. The
  room is locked for the whole series; one range query supplies all existing bookings.
- **Recurring is atomic by default.** Any conflict → `409` and nothing is written; every
  conflicting occurrence is listed. With `skipConflicts: true` the free occurrences are
  created and conflicting ones are returned in `skipped[]`. If *all* conflict, `409` — no
  empty series. The frontend exposes this as “Skip conflicting occurrences and create the rest”.
- **Capacity is not bypassable via a partially filled form:** if both `attendeeCount` and
  `attendees` are sent they must match; otherwise `400 ATTENDEE_COUNT_MISMATCH`.
- **Times are office-local wall-clock values** (`LocalDateTime`, no offset). This avoids
  DST/offset bugs for a single-office booking system; the office zone (`Europe/London` by
  default) is only used for “today/now” decisions. This is documented in `API.md`.

---

## API at a glance

Full request/response schemas and error codes live in [`API.md`](API.md) and Swagger.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/rooms` | List seeded rooms (capacity, floor, amenities) |
| GET | `/api/rooms/{id}/availability?date=` | Busy + free timeline for one day |
| POST / GET | `/api/bookings` | Create / search (room, organiser, status, date, range, paging) |
| GET / PUT / DELETE | `/api/bookings/{id}` | Read / full update (optimistic `version`) / hard delete |
| PATCH | `/api/bookings/{id}/cancel` | Cancel, idempotent, frees the slot |
| GET | `/api/bookings/{id}/ics` | RFC 5545 calendar download |
| GET | `/api/find-slot` | Earliest slot + alternatives |
| POST | `/api/bookings/recurring/preview` | Per-occurrence conflict preview (writes nothing) |
| POST | `/api/bookings/recurring` | Create series (atomic or skip-conflicts) |
| GET | `/api/series`, `/api/series/{id}` | List / inspect series and occurrences |
| DELETE | `/api/series/{id}?from=` | Cancel future confirmed occurrences |

Errors are RFC 9457 `application/problem+json` with a stable `code`
(`BOOKING_CONFLICT`, `CAPACITY_EXCEEDED`, `RECURRING_CONFLICT`, `STALE_VERSION`, …),
field-level `errors`, conflict details and a per-request `requestId`.

---

## Design notes

### Architecture

```
web/        controllers, DTO records, RFC 9457 error handler
service/    BookingService, RecurringBookingService, SlotService, RoomService,
            OfficeHours, Attendees, FreeWindows, RecurrenceGenerator, IcsService
domain/     JPA entities (Room, Booking, BookingSeries) + BookingStatus
repo/       Spring Data repositories (including pessimistic room lock)
config/     typed properties, security, OpenAPI, room seeding, request id/size filters
```

- Constructor injection throughout; no field injection, no Lombok, no cyclic dependencies.
- Controllers are thin and never expose entities; DTOs are Java records with Bean Validation.
- Business rules live in services/`OfficeHours`, not controllers.
- Flyway owns the schema (`ddl-auto=validate`), so schema drift fails fast.
- `spring.jpa.open-in-view=false` — lazy data is mapped inside transactions.
- Hibernate `default_batch_fetch_size=50` avoids N+1 for attendee collections in pages.

### Why these choices

| Decision | Rationale |
|---|---|
| Half-open intervals | Back-to-back bookings are unambiguous and no “1-minute gap” bug is possible |
| Pessimistic lock per room | Correct under real concurrency, DB-independent, simple to reason about; optimistic `@Version` also protects booking edits |
| 400 for capacity, 409 for overlap | Capacity is an invalid request against a known room constraint; overlap is a conflict with current state. Both are documented and machine-readable via `code` |
| Atomic recurrence default | Prevents half-created series; partial creation is an explicit opt-in |
| `LocalDateTime` wall-clock | Single office; no user-visible offset math; DST-safe for booking hours |
| H2 file + Flyway + Postgres driver | Zero-setup demo, production-shaped migration path |
| Basic auth, BCrypt, stateless | Small but real security boundary; env-overridable credentials; CSRF disabled correctly for a stateless API |

### Edge cases covered (and tested)

- Overlaps: partial, contained, containing, exact duplicate, update-into-overlap, cancelled
  slot reuse, different rooms at the same time, back-to-back on both sides.
- Intervals: end ≤ start, overnight, outside 09:00–18:00, 15-minute minimum, exact 18:00
  finish, non-whole-minute timestamps, 540-minute all-day booking.
- Capacity/attendees: count only, list only, both matching, both mismatching, duplicates,
  zero, above room capacity, >50 names.
- Find-slot: busy rooms, fully booked, capacity/amenity filters, room filter, off-grid
  existing booking, no match, past date, invalid duration/headcount, today’s past hours,
  and a 09:00–18:00 full-day booking.
- Recurrence: default weekday, multiple weekdays, mid-week start, year boundary, duplicate
  weekdays, no occurrences, max 52 weeks / 366 occurrences, all-conflict, partial
  skip-conflicts, per-occurrence conflict details, cancel-future-only, preview is read-only.
- Robustness: malformed JSON, unknown fields are ignored, validation errors, wrong UUID,
  unknown room/booking/series, wrong method/content type, 128 KB body limit, optimistic
  stale version, lock contention, 401/403 with `WWW-Authenticate`, public health, restricted
  CORS, request-id sanitisation and echo.
- Calendar export: ICS special-character escaping (comma/semicolon/backslash/newline),
  line folding at 75 octets, injection of fake `ATTENDEE` lines prevented.
- Seed loader: validates room ids/capacities, rejects duplicates, never overwrites existing rooms.

### Security

- HTTP Basic with BCrypt-hashed in-memory user; credentials from `APP_ADMIN_*` env vars.
- Stateless sessions, CSRF disabled (correct without cookies), security headers
  (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`).
- CORS allow-list from config (only the Vite dev origin by default).
- All queries parameterised through Spring Data; no dynamic SQL/sort injection.
- Generic 500 responses; details only in logs with the request id.
- Request body size limit, Bean Validation everywhere, explicit serialisation of DTOs.
- Swagger/health are public in this demo; set `springdoc.*.enabled=false` and secure them
  before production. TLS termination is assumed (reverse proxy).

### Performance

- Overlap lookup uses index `(room_id, start_at, end_at)`; listing filters are paged and
  capped at 100 rows.
- Recurrence conflict detection uses one range query for the whole series, then in-memory
  interval matching — not one query per occurrence.
- Find-slot loads one day’s bookings for all candidate rooms once, computes free windows
  per room, and never scans historical data. Complexity ~`rooms × (busy + slots)`.
- Room locking is per room, so unrelated bookings proceed in parallel.
- Batch fetching keeps page endpoints at a bounded number of queries.

### Known limitations / next steps

- Single demo user (no per-organiser ownership or roles beyond authentication).
- No email/calendar invites beyond ICS download; no reminders.
- Series edits apply per occurrence only; the series template is immutable (cancel + recreate
  is the supported flow).
- No rate limiting or audit table (request ids and timestamps are logged).
- H2 is fine for the demo; use PostgreSQL for multi-instance deployments (the room-row lock
  then serialises across instances).
- Times are wall-clock for one office; multi-timezone support would require storing UTC
  instants plus an IANA zone per room.

---

## Verification performed

- `mvn test` — **81 tests, 0 failures** (unit + MockMvc integration + concurrency).
- `mvn -DskipTests package` — executable jar.
- Real HTTP smoke test: rooms, create `201`, duplicate/overlap `409` with conflict details,
  back-to-back `201`, find-slot `200`, unauthenticated `401`, OpenAPI `200`.
- Frontend `npm run build` (type-checked) and `npm test`.

See [`PROMPTS.md`](PROMPTS.md) for the AI collaboration log, including the bugs the tests
caught and how they were fixed.
