# Meeting Room Booking Engine

A zero-dependency Node.js backend for an office room-booking system. Handles CRUD on
bookings, overlap/capacity enforcement, smart slot-finding, and weekly recurrences.

## Quick start

```bash
node src/index.js
```

Server starts on `http://localhost:3000` (override with `PORT` env var).

## API

All requests and responses use `Content-Type: application/json`.

### Create a booking

```
POST /api/bookings

{
  "roomId": "meeting-1",
  "title": "Sprint sync",
  "organiser": "alice@example.com",
  "start": "2026-10-28T10:00:00.000Z",
  "end":   "2026-10-28T11:00:00.000Z",
  "attendees": ["bob@example.com"]
}
```

Returns `201` with the booking object (including generated `id`).  
Returns `409` if the room is already booked in that window.  
Returns `400` if attendees exceed room capacity.

### List bookings

```
GET /api/bookings
```

### Get a booking

```
GET /api/bookings/:id
```

### Update a booking

```
PUT /api/bookings/:id
{ "title": "Updated title", "attendees": ["carol@example.com"] }
```

Partial updates — only send the fields to change.

### Delete a booking

```
DELETE /api/bookings/:id
```

Returns `204` on success.

### Find slot (earliest free room & time)

```
GET /api/bookings/find-slot?duration=60&attendees=5&date=2026-10-28
```

Searches all rooms (smallest-capacity-first that fits `attendees`) in 30‑minute
granularity from 09:00 to 18:00. Returns the earliest matching slot:

```json
{
  "room": { "id": "conference-b", "name": "Conference B", "capacity": 8, "floor": 2 },
  "start": "2026-10-28T09:00:00.000Z",
  "end":   "2026-10-28T10:00:00.000Z"
}
```

Returns `404` if no slot is available.

### Weekly recurring booking

```
POST /api/bookings/recurring

{
  "roomId": "meeting-1",
  "title": "Weekly standup",
  "organiser": "alice@example.com",
  "start": "2026-10-28T10:00:00.000Z",
  "end":   "2026-10-28T11:00:00.000Z",
  "attendees": ["bob@example.com"],
  "recurrence": "weekly",
  "recurrenceEnd": "2026-12-16"
}
```

Creates a booking for each weekly occurrence and reports any conflicts:

```json
{
  "ok": true,
  "booking": { ... },
  "occurrences": [ ... ],
  "conflicts": [
    {
      "date": "2026-11-04",
      "reason": "Overlaps with \"Blocking booking\""
    }
  ]
}
```

## Running tests

```bash
node --test src/**/*.test.js
```

## Design decisions

- **Zero external dependencies** — runs on plain Node.js (20+). No npm install needed.
- **JSON file persistence** — `data/bookings.json` written after every mutation.
- **Service layer** — business logic lives in `services.js`; HTTP routing in `server.js`.
- **Overlap detection** — `startA < endB && endA > startB` (strict `<` allows back-to-back).
- **Slot finder** — slides a 30‑minute window; picks the smallest-capacity room that fits.
- **Recurring bookings** — expanded eagerly on creation; each occurrence is created as an individual booking so future conflict checks see them. Conflicts are returned in the response.

## Stretch / Bonus

- In-memory cache avoids re-reading `rooms.json` after first load.
- CORS headers for cross-origin dev clients.
- Room capacity floor plan (`data/rooms.json`) is extensible with extra fields.