# Meeting Room Booking Engine (PS2)

Backend API for booking meeting rooms, with overlap detection, capacity
enforcement, slot search and weekly recurrence.

## Stack
Python 3.10+ · FastAPI · Pydantic · pytest. Persistence is a JSON file
(`app/bookings.json`) behind an in-process lock — no database needed.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Interactive docs at http://127.0.0.1:8000/docs

## Test
```bash
pytest -q
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/rooms` | List rooms (id, name, capacity) |
| POST | `/bookings` | Create a booking |
| GET | `/bookings` | List (optional `room_id`, `from`, `to`) |
| GET | `/bookings/{id}` | Read one |
| PUT | `/bookings/{id}` | Update (full replace) |
| DELETE | `/bookings/{id}` | Delete |
| GET | `/slots/find?duration_mins=&attendees=&date=` | Earliest free slot |

Booking payload:
```json
{
  "room_id": "r1",
  "organiser": "bob@corp.com",
  "start": "2026-11-02T09:00:00",
  "end": "2026-11-02T10:00:00",
  "attendees": ["alice@corp.com"],
  "recurrence": { "count": 3 }        // optional; or { "until": "2026-11-16T09:00:00" }
}
```

## Behaviour & rules
- **Overlaps** (M2): rejected per room. Intervals are half-open `[start, end)`,
  so back-to-back (`end == next.start`) is allowed.
- **Capacity** (M3): `len(attendees) <= room.capacity`, enforced on create & update.
- **Find-slot** (M4): business hours 09:00–18:00; earliest time wins, tie-break by
  smallest room that fits the attendee count.
- **Recurrence** (M5): weekly; conflicts reported per occurrence with its window.
- **Validation**: `start < end`, whole-minute alignment, within business hours,
  non-empty attendees, positive duration/attendee count.

## Error responses
- `400/422` invalid input · `404` unknown room/booking/no slot · `409` conflict
  with a per-occurrence `conflicts[]` detail (reason: `overlap` | `capacity`).

## Layout
```
app/{main,models,store,service}.py
app/rooms.json          # seed rooms
tests/                  # pytest suite covering all milestones + edge cases
```
