# Meeting Room Booking Engine

Spring Boot 3.5 · Java 21 · Spring Data JPA · H2 in-memory. Implements M1–M5 plus the
utilization analytics stretch goal.

## Run

```bash
mvn spring-boot:run          # http://localhost:8080
mvn test                     # 66 integration tests
```

If Maven cannot reach Central through a TLS-inspecting proxy, add
`-Djavax.net.ssl.trustStoreType=WINDOWS-ROOT`.

Seeded rooms (`CommandLineRunner`): **Room A** cap 5, **Room B** cap 10, **Room C** cap 20.

## Operating window

Bookings live inside **09:00–18:00 UTC, Monday–Friday**. The window is half-open —
`[start, end)` — so `09:00-10:00` and `10:00-11:00` are both valid and never conflict.
All instants are normalised to UTC on write, so `09:00Z` and `14:30+05:30` are recognised
as the same moment rather than slipping past each other.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/bookings` | M1 create → `201` + `Location` |
| `GET` | `/api/bookings?roomId=` | M1 list (optionally per room) |
| `GET` | `/api/bookings/{id}` | M1 read |
| `PUT` | `/api/bookings/{id}` | M1 reschedule (re-validates overlap) |
| `DELETE` | `/api/bookings/{id}` | M1 delete → `204` |
| `GET` | `/api/rooms` | Seeded inventory |
| `GET` | `/api/bookings/find-slot?duration=&attendeeCount=&date=` | M4 best-fit earliest slot |
| `POST` | `/api/bookings/recurring/dry-run?occurrences=` | M5 step 1 — validate, persist nothing |
| `POST` | `/api/bookings/recurring/confirm` | M5 step 2 — commit the vetted plan |
| `GET` | `/api/analytics/utilization?weekStart=` | Stretch — per-room utilization |

### Create a booking (M1–M3)

```bash
curl -X POST localhost:8080/api/bookings -H 'Content-Type: application/json' -d '{
  "roomId": 1, "organiser": "Priya",
  "startTime": "2026-11-02T09:00:00Z", "endTime": "2026-11-02T10:00:00Z",
  "attendees": ["dev-1@example.com", "dev-2@example.com"]
}'
```

Rejections are specific: `400` when `attendees.size() > room.capacity`
(`"attendees (6) exceed Room A capacity (5)"`), when a window falls outside operating
hours, when attendees repeat (`"attendees must be unique; duplicated: dev@example.com"`),
or when `startTime` is in the past. Overlaps return `409` with the blocking bookings listed.

### Find a slot (M4)

```bash
curl 'localhost:8080/api/bookings/find-slot?duration=60&attendeeCount=8&date=2026-11-02'
# {"roomId":2,"roomName":"Room B","roomCapacity":10,
#  "startTime":"2026-11-02T09:00:00Z","endTime":"2026-11-02T10:00:00Z"}
```

Rooms are scanned **smallest capacity first**, so an 8-person group takes Room B and leaves
Room C free for larger groups. Within a room the day is swept from 09:00 and the sweep jumps
past each conflicting booking instead of stepping minute-by-minute. The last offerable
window is `17:00-18:00`; a request that only fits with a spill past 18:00 is not offered.
`404` when nothing fits.

### Weekly recurrence (M5)

Step 1 validates the series and returns a per-date verdict. Nothing is persisted.

```bash
curl -X POST 'localhost:8080/api/bookings/recurring/dry-run?occurrences=4' \
  -H 'Content-Type: application/json' -d '{
  "roomId": 2, "organiser": "Standup",
  "startTime": "2026-11-02T14:00:00Z", "endTime": "2026-11-02T15:00:00Z",
  "attendees": ["dev-1@example.com"]
}'
```

```json
{
  "planToken": "eyJyb29tSWQiOjIs...",
  "executable": true, "allAvailable": false,
  "requestedOccurrences": 4, "availableCount": 3, "conflictCount": 1,
  "occurrences": [
    {"startTime":"2026-11-02T14:00:00Z","endTime":"2026-11-02T15:00:00Z",
     "available":false,"reason":"conflicts with 2026-11-02T14:00Z-15:00Z (Fixture)"},
    {"startTime":"2026-11-09T14:00:00Z","endTime":"2026-11-09T15:00:00Z","available":true,"reason":null}
  ],
  "commitEndpoint": "/api/bookings/recurring/confirm",
  "expiresAt": "2026-10-27T12:15:00Z"
}
```

Step 2 commits. The client may send the whole plan, or select only the dates it wants — the
`occurrences` array is optional and any slot not in the signed plan is rejected. Slots taken
in the meantime are skipped and reported, never double-booked.

```bash
curl -X POST localhost:8080/api/bookings/recurring/confirm \
  -H 'Content-Type: application/json' \
  -d '{"planToken":"eyJyb29tSWQiOjIs..."}'          # omit "occurrences" to accept all
# {"savedCount":3,"skippedCount":0,"savedBookings":[...],"skipped":[]}
```

The token is a base64 payload plus HMAC-SHA256 signature — server-side state is not required
to trust the roster of vetted slots. It expires after 15 minutes (`booking.plan-token.ttl`).

### Utilization

```bash
curl 'localhost:8080/api/analytics/utilization?weekStart=2026-11-02'
# {"from":"2026-11-02T09:00:00Z","to":"2026-11-09T09:00:00Z","workingHoursPerDay":540,
#  "rooms":[{"roomName":"Room A","bookedMinutes":90,"availableMinutes":2700,
#            "utilizationPercent":3.33}, ...]}
```

Denominator is bookable time only (5 weekdays × 540 minutes), so a fully booked room reads
100%. Any date in the week normalises back to its Monday.

## Concurrency

Double-booking is prevented by `RoomRepository.findByIdForUpdate` — a
`@Lock(PESSIMISTIC_WRITE)` row lock taken **before** the overlap check in every mutating
path. Two transactions can therefore never both read "no conflict" and both insert.
`BookingConcurrencyIntegrationTest` fires 12 simultaneous identical requests and asserts
exactly one winner and one persisted row, and 24 randomised overlapping requests and asserts
no pair of committed bookings overlaps.

## Error shape

```json
{"timestamp":"2026-11-02T09:00:00Z","status":409,"error":"Conflict",
 "message":"Room A is already booked during the requested window",
 "path":"/api/bookings","details":["2026-11-02T09:00Z-10:00Z (Fixture)"]}
```

`400` malformed input / capacity / outside hours · `404` unknown room, booking, or no
availability · `409` overlap, or a slot taken between dry-run and confirm.

## Layout

```
src/main/java/com/sdsi/booking/
├── domain/        Room, Booking (half-open overlap predicate)
├── repository/    pessimistic-lock and overlap queries
├── service/       BookingService, FindSlotService, RecurrenceService,
│                  PlanTokenService, UtilizationService, BusinessHours, AttendeeRules
└── web/           REST controllers, DTOs, GlobalExceptionHandler
```
