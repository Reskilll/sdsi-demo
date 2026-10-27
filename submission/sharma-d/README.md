# Meeting Room Booking Engine

Spring Boot backend for office room-booking. In-memory storage, zero external dependencies beyond Spring Boot.

## Quick Start

```bash
cd submission/sharma-d
./mvnw spring-boot:run          # requires Maven wrapper or local Maven
# or
mvn spring-boot:run
```

Runs on **http://localhost:8080**.

## Sample Data

5 rooms preloaded (see `src/main/resources/data/rooms.json`):

| Room | Capacity |
|------|---------|
| Atlas (r1) | 4 |
| Boardroom (r2) | 8 |
| Conference-A (r3) | 12 |
| Conference-B (r4) | 20 |
| Town Hall (r5) | 50 |

## API Reference

### M1 — Create a Booking
```
POST /api/bookings
Content-Type: application/json

{"roomId":"r2","organiser":"alice","date":"2026-11-01",
 "start":"10:00","end":"11:00","attendees":["alice","bob"]}
```
→ `201 Created` with the full Booking object (includes generated `id`).

### M1 — Get a Booking
```
GET /api/bookings/{id}
```

### M1 — List All Bookings
```
GET /api/bookings
```

### M1 — Update a Booking
```
PUT /api/bookings/{id}
Content-Type: application/json

{"roomId":"r3","organiser":"alice","date":"2026-11-01",
 "start":"11:00","end":"12:00","attendees":["alice","bob","carol"]}
```
→ Overlap + capacity checks apply.

### M1 — Delete a Booking
```
DELETE /api/bookings/{id}
→ 204 No Content
```

### M4 — Find Earliest Free Slot
```
POST /api/bookings/find-slot
Content-Type: application/json

{"durationMinutes":60,"attendeeCount":5,"date":"2026-12-01"}
```
→ Returns the earliest available room+time across all rooms that fit the attendee count, between 09:00-18:00.

### M5 — Recurring Weekly Booking
```
POST /api/bookings/recurring
Content-Type: application/json

{"roomId":"r3","organiser":"mike","startDate":"2026-11-09",
 "endDate":"2026-11-23","start":"14:00","end":"15:00",
 "attendees":["mike","nina"]}
```
→ Creates a booking for every Monday in the range. Response includes `successful` (list of created bookings) and `conflicts` (list of dates that conflicted, with reasons).

## Error Responses

| Status | When |
|--------|------|
| `400 Bad Request` | Invalid input (validation, end ≤ start, outside 09:00-18:00) |
| `404 Not Found` | Unknown room or booking ID |
| `409 Conflict` | Overlapping booking on same room |
| `422 Unprocessable Entity` | Attendees exceed room capacity |

## Design Decisions

- **Business hours**: 09:00–18:00, enforced on create & update.
- **Back-to-back**: `endsAt == next.startsAt` is allowed (no gap required).
- **Find-slot**: scans rooms in ascending-capacity order; returns the earliest slot across all rooms.
- **Recurring**: weekly, same day-of-week. Partial success — conflicting occurrences are reported but non-conflicting ones are created.
- **In-memory store**: `ConcurrentHashMap` — thread-safe, no database needed.
- **Time-only overlap**: bookings on different dates never conflict.

## Running Tests

```bash
mvn test
```

18 integration tests covering:
- M1: CRUD operations
- M2: Overlap rejection + back-to-back allowance
- M3: Capacity enforcement
- M4: Find-slot (empty day, partially booked, no suitable room)
- M5: Recurring bookings (all clean, partial conflict)
- Validation: missing fields, invalid times, out-of-hours, unknown room