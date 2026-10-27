# Meeting Room Booking API — Contract

Backend: Spring Boot 3.5, base URL `http://localhost:8080`, API root `/api`.
Interactive docs: `GET /swagger-ui.html` and `GET /v3/api-docs` (public in this demo).

## Conventions

- **Auth:** HTTP Basic on every `/api/**` call. Demo user: `admin` / `admin123`
  (override with `APP_ADMIN_USERNAME`, `APP_ADMIN_PASSWORD`). `GET /actuator/health` is public.
- **Times are office-local wall-clock values** in ISO-8601 **without offset**:
  - date-time: `"2026-11-02T10:00:00"` (`LocalDateTime`; seconds may be omitted on input)
  - date: `"2026-11-02"`
  - time: `"10:00:00"` (`LocalTime`)
  - Do **not** convert with JavaScript `Date` timezone logic; format the string parts directly.
- **Office hours:** 09:00–18:00, every day. Minimum booking 15 minutes. Times must be on the same day.
- **Overlap rule:** half-open intervals. Existing `start < new.end AND existing.end > new.start`.
  Back-to-back bookings (10:00–11:00 and 11:00–12:00) are allowed.
- **Pagination:** `page` (0-based, default 0), `size` (default 20, max 100).
  Response shape: `{ content, page, size, totalElements, totalPages, first, last }`.
- **IDs:** rooms are slugs (`atlas`); bookings and series are UUIDs.
- **Seed rooms:** `kepler` (2), `atlas` (4), `orion` (8), `vega` (12), `helios` (16), `lumen` (24).

## Errors

All failures use RFC 9457 `application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Conflict",
  "status": 409,
  "detail": "The requested slot overlaps 1 existing booking(s) in this room.",
  "instance": "/api/bookings",
  "code": "BOOKING_CONFLICT",
  "timestamp": "2026-10-27T09:00:00Z",
  "requestId": "2f0c...",
  "conflicts": [
    { "bookingId": "uuid", "title": "Planning", "organiser": "Ritvik",
      "start": "2026-11-02T10:00:00", "end": "2026-11-02T11:00:00" }
  ]
}
```

Recurring conflicts add `occurrences` (conflicting occurrences only), `conflictCount`,
`totalOccurrences`. Validation failures (400) add
`errors: [{ "field": "title", "message": "must not be blank" }]`.

| Status | `code` examples | Meaning |
|---|---|---|
| 400 | `VALIDATION_FAILED`, `INVALID_JSON`, `INVALID_PARAMETER`, `MISSING_PARAMETER`, `CAPACITY_EXCEEDED`, `OUTSIDE_OFFICE_HOURS`, `INVALID_INTERVAL`, `INVALID_DURATION`, `ATTENDEE_COUNT_MISMATCH`, `ATTENDEES_REQUIRED`, `DATE_IN_PAST`, `INVALID_PAGE_SIZE`, `BOOKING_CANCELLED` | Bad input / business rule |
| 401 | `UNAUTHORIZED` | Missing/invalid Basic credentials |
| 403 | `FORBIDDEN` | Access denied |
| 404 | `NOT_FOUND` | Unknown room/booking/series or path |
| 405 | `METHOD_NOT_ALLOWED` | Wrong HTTP method |
| 409 | `BOOKING_CONFLICT`, `RECURRING_CONFLICT`, `STALE_VERSION`, `CONCURRENT_MODIFICATION`, `DATA_INTEGRITY` | Conflict with existing state |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Body is not JSON |
| 500 | `INTERNAL_ERROR` | Unexpected (details only in server logs; quote `requestId`) |

All responses echo `X-Request-Id`.

---

## Rooms

### `GET /api/rooms`

```json
[
  { "id": "atlas", "name": "Atlas", "capacity": 4, "floor": 1,
    "location": "North Wing", "amenities": ["tv", "video", "whiteboard"] }
]
```

Amenities seen in seeds: `tv`, `video`, `whiteboard`, `projector`, `speakerphone`, `accessibility`.

### `GET /api/rooms/{id}`

`200` room or `404`.

### `GET /api/rooms/{id}/availability?date=YYYY-MM-DD`

```json
{
  "room": { "id": "atlas", "name": "Atlas", "capacity": 4, "floor": 1,
            "location": "North Wing", "amenities": ["tv"] },
  "date": "2026-11-02",
  "busy": [
    { "start": "2026-11-02T10:00:00", "end": "2026-11-02T11:00:00",
      "bookingId": "uuid", "title": "Planning", "organiser": "Ritvik" }
  ],
  "free": [
    { "start": "2026-11-02T09:00:00", "end": "2026-11-02T10:00:00", "minutes": 60 },
    { "start": "2026-11-02T11:00:00", "end": "2026-11-02T18:00:00", "minutes": 420 }
  ]
}
```

Only `CONFIRMED` bookings count as busy. `date` is required.

---

## Bookings

Booking object:

```json
{
  "id": "uuid",
  "room": { "id": "atlas", "name": "Atlas", "capacity": 4, "floor": 1,
            "location": "North Wing", "amenities": ["tv"] },
  "organiser": "Ritvik",
  "organiserEmail": "ritvik@example.com",
  "title": "Planning",
  "description": "Sprint planning",
  "start": "2026-11-02T10:00:00",
  "end": "2026-11-02T11:00:00",
  "attendeeCount": 4,
  "attendees": ["Ada", "Grace"],
  "status": "CONFIRMED",
  "seriesId": null,
  "occurrenceIndex": null,
  "createdAt": "2026-10-27T09:00:00Z",
  "updatedAt": "2026-10-27T09:00:00Z",
  "version": 0
}
```

`status` is `CONFIRMED` or `CANCELLED`.

### `POST /api/bookings` → `201` + `Location: /api/bookings/{id}`

```json
{
  "roomId": "atlas",
  "organiser": "Ritvik",
  "organiserEmail": "ritvik@example.com",
  "title": "Planning",
  "description": "Sprint planning",
  "start": "2026-11-02T10:00:00",
  "end": "2026-11-02T11:00:00",
  "attendeeCount": 4,
  "attendees": ["Ada", "Grace"]
}
```

- `attendeeCount` and/or `attendees` required. If both are sent they must agree after dedupe,
  otherwise `400 ATTENDEE_COUNT_MISMATCH`.
- Capacity is checked against the effective count (`400 CAPACITY_EXCEEDED`).
- Overlap → `409 BOOKING_CONFLICT` with `conflicts[]`.
- `attendees` max 50 named entries; each ≤120 chars.

### `GET /api/bookings/{id}` → `200` booking (including cancelled) or `404`

### `PUT /api/bookings/{id}` → `200` updated booking

Full replacement body = same as create plus optional `version`.
If `version` is supplied and stale → `409 STALE_VERSION`.
Cancelled bookings cannot be updated (`400 BOOKING_CANCELLED`).
Re-validates capacity, hours and overlaps (excluding itself).

### `PATCH /api/bookings/{id}/cancel` → `200` cancelled booking (idempotent)

Frees the slot for new bookings; the booking is retained for audit.

### `DELETE /api/bookings/{id}` → `204` (hard delete)

### `GET /api/bookings/{id}/ics` → `text/calendar` attachment

Calendar file with floating local times. User text is escaped against ICS injection.

### `GET /api/bookings` → page of bookings

Optional query params: `roomId`, `organiser` (case-insensitive exact),
`status` (`CONFIRMED`/`CANCELLED`), `seriesId`, `date` (whole day),
`from`/`to` (ISO date-time, overlap filter), `page`, `size`.
Use either `date` or `from`/`to`, not both (`400 INVALID_FILTER`). Sorted by start ascending.

Examples:

```bash
curl -u admin:admin123 "http://localhost:8080/api/bookings?date=2026-11-02&size=100"
curl -u admin:admin123 "http://localhost:8080/api/bookings?roomId=atlas&from=2026-11-02T09:00:00&to=2026-11-02T18:00:00"
```

---

## Find a slot (M4)

### `GET /api/find-slot` (alias: `GET /api/slots`)

| Param | Required | Notes |
|---|---|---|
| `date` | yes | not in the past (`400 DATE_IN_PAST`) |
| `durationMinutes` | yes | 15–540 |
| `attendees` | yes | ≥1 |
| `amenities` | no | repeatable or comma-separated, ALL must match (case-insensitive) |
| `roomId` | no | restrict to one room |

```json
{
  "date": "2026-11-02",
  "durationMinutes": 60,
  "attendees": 4,
  "slot": {
    "start": "2026-11-02T09:00:00",
    "end": "2026-11-02T10:00:00",
    "room": { "id": "atlas", "name": "Atlas", "capacity": 4, "...": "..." }
  },
  "alternatives": [
    { "start": "2026-11-02T09:00:00", "end": "2026-11-02T10:00:00", "room": { "id": "orion", "...": "..." } }
  ],
  "message": null
}
```

- Earliest start across all suitable rooms; ties broken by smaller capacity then name.
- Candidate starts lie on a 15-minute grid; the booking must end by 18:00.
- Today's already-past times are skipped; if the day is over, `slot` is absent and `message` explains why.
- No match → `200` with `slot` absent and `message` (not an error).

---

## Weekly recurring bookings (M5)

Request body (`POST /api/bookings/recurring` and `/preview`):

```json
{
  "roomId": "atlas",
  "organiser": "Ritvik",
  "organiserEmail": "ritvik@example.com",
  "title": "Weekly sync",
  "description": "Team sync",
  "startsOn": "2026-11-02",
  "startTime": "10:00",
  "endTime": "11:00",
  "daysOfWeek": ["MONDAY", "WEDNESDAY"],
  "weeks": 4,
  "attendeeCount": 4,
  "attendees": ["Ada", "Grace"],
  "skipConflicts": false
}
```

- `weeks` 1–52. Occurrences fall inside a window of `weeks` weeks starting on the **Monday**
  of the week containing `startsOn`; dates before `startsOn` are skipped.
- `daysOfWeek` optional; defaults to the weekday of `startsOn`. Max 7, enum names uppercase.
- Max 366 occurrences per series.
- Same validation as a single booking (hours, capacity, attendee pairing).

### `POST /api/bookings/recurring/preview` → `200`, writes nothing

```json
{
  "startsOn": "2026-11-02",
  "weeks": 4,
  "daysOfWeek": ["MONDAY"],
  "occurrenceCount": 4,
  "conflictCount": 1,
  "occurrences": [
    { "start": "2026-11-02T10:00:00", "end": "2026-11-02T11:00:00",
      "status": "FREE", "conflicts": [] },
    { "start": "2026-11-09T10:00:00", "end": "2026-11-09T11:00:00",
      "status": "CONFLICT",
      "conflicts": [
        { "bookingId": "uuid", "title": "Overlap", "organiser": "Sam",
          "start": "2026-11-09T10:30:00", "end": "2026-11-09T11:30:00" }
      ] }
  ]
}
```

### `POST /api/bookings/recurring` → `201` (at least one occurrence created)

```json
{
  "seriesId": "uuid",
  "series": { "id": "uuid", "room": { "...": "..." }, "title": "Weekly sync",
              "startTime": "10:00:00", "endTime": "11:00:00",
              "startsOn": "2026-11-02", "weeks": 4,
              "daysOfWeek": ["MONDAY"], "attendeeCount": 4,
              "attendees": ["Ada"], "createdAt": "2026-10-27T09:00:00Z" },
  "created": [ { "...": "Booking" } ],
  "skipped": [ { "...": "OccurrenceView with status CONFLICT" } ],
  "message": "Created 3 of 4 occurrence(s); 1 skipped due to conflicts."
}
```

- Default (`skipConflicts=false`): **atomic**. Any conflict → `409 RECURRING_CONFLICT`,
  nothing is created, all conflicting occurrences are reported.
- `skipConflicts=true`: create only free occurrences. If **all** conflict → `409` (no empty series).
- Conflict detection covers the whole span with one query under a room lock.

### `GET /api/series?page=&size=` → page of series summaries

Summary fields: `id, room, organiser, organiserEmail, title, description,
startTime, endTime, startsOn, weeks, daysOfWeek, attendeeCount, attendees, createdAt`.

### `GET /api/series/{id}` → summary + `occurrences: Booking[]` (all statuses, start ascending)

### `DELETE /api/series/{id}?from=YYYY-MM-DDTHH:mm:ss` → `200`

Cancels `CONFIRMED` occurrences starting at/after `from` (default: now); earlier occurrences
are kept for audit. Response: `{ "seriesId": "uuid", "cancelledCount": 3 }`.

---

## Examples

```bash
# Create
curl -u admin:admin123 -H "Content-Type: application/json" \
  -d '{"roomId":"atlas","organiser":"Ritvik","title":"Planning",
       "start":"2026-11-02T10:00:00","end":"2026-11-02T11:00:00","attendeeCount":4}' \
  http://localhost:8080/api/bookings

# Earliest 60-minute slot for 6 people
curl -u admin:admin123 \
  "http://localhost:8080/api/find-slot?date=2026-11-02&durationMinutes=60&attendees=6"

# Recurring preview
curl -u admin:admin123 -H "Content-Type: application/json" \
  -d '{"roomId":"atlas","organiser":"Ritvik","title":"Weekly sync",
       "startsOn":"2026-11-02","startTime":"10:00","endTime":"11:00",
       "weeks":4,"daysOfWeek":["MONDAY"],"attendeeCount":4}' \
  http://localhost:8080/api/bookings/recurring/preview
```

## Status codes for the five judged behaviours

| Requirement | Success | Rejection |
|---|---|---|
| M1 CRUD | `201`, `200`, `204` | `400`, `404`, `409` |
| M2 overlap | back-to-back `201` | overlap `409 BOOKING_CONFLICT` |
| M3 capacity | within capacity `201` | `400 CAPACITY_EXCEEDED` |
| M4 find slot | `200` with `slot` | no match `200` + `message`; bad date `400` |
| M5 recurring | `201` with per-occurrence results | `409 RECURRING_CONFLICT` with `occurrences` |
