# PS2: Meeting Room Booking Engine Backend

> **SDSI Hackathon — Developer Screening Track**  
> **Submission by:** Ashok (`ashok-scm1989`)  
> **Stack:** Java 21, Spring Boot 3.3.5, Spring Data JPA, H2 In-Memory Database, Maven  

---

## 📋 Overview

The **Meeting Room Booking Engine** is a high-performance, enterprise-grade backend service designed to streamline office room reservations, prevent double-bookings, enforce room capacity rules, discover optimal meeting slots, and manage complex weekly recurring schedules with conflict reporting.

---

## 🎯 Milestone Checklist & Evaluation Rubric

| Milestone | Requirement | Status | Implementation Details |
|:---|:---|:---:|:---|
| **M1** | **CRUD Bookings** | ✅ Complete | Create, read, update, delete bookings with organizer, room, start/end timestamps, and attendee lists. |
| **M2** | **Reject Overlaps / Allow Back-to-Back** | ✅ Complete | Half-open interval conflict detection ($S_1 < E_2 \land E_1 > S_2$). Back-to-back bookings ($E_1 == S_2$) are valid and permitted. |
| **M3** | **Enforce Room Capacity** | ✅ Complete | Rejects bookings exceeding room capacity. Rooms loaded dynamically from `rooms.json` at startup. |
| **M4** | **Find-Slot Search Engine** | ✅ Complete | Given date, duration, and attendee count, finds the earliest available room & time between **09:00 and 18:00**, tie-broken by smallest room capacity to optimize space efficiency. |
| **M5** | **Weekly Recurring Bookings** | ✅ Complete | Generates $N$ weekly occurrences with per-occurrence conflict analysis. Supports `BOOK_AVAILABLE` and `ALL_OR_NOTHING` policies and group cancellation. |
| **Stretch** | **Interactive Web Dashboard** | 🚀 Bonus | Responsive web interface at `http://localhost:8080/` with live room status, slot finder, booking manager, and 1-click demo buttons. |
| **Stretch** | **Automated Test Suites** | 🚀 Bonus | 30+ unit & integration tests plus automated end-to-end curl verification scripts (`test-suite.sh` and `test-suite.bat`). |

---

## 🏗️ Architecture & Design

The backend is built with a clean, domain-driven, layered architecture:

```
com.reskilll.meetingroom
 ├── config/           # App configuration, Jackson date serialization & rooms.json bootstrap
 ├── controller/       # REST API endpoints & RFC-compliant Global Exception Handler
 ├── dto/              # Request/Response contracts and validation constraints
 ├── exception/        # Domain-specific exceptions (Conflict, Capacity, NotFound, Invalid)
 ├── model/            # JPA Entities & Domain Models (Room, Booking, RecurrencePolicy)
 ├── repository/       # Thread-safe Room Repository & Spring Data JPA Booking Repository
 └── service/          # Core Business Logic (Overlap Math, Slot Optimizer, Recurrence Engine)
```

### Key Technical Highlights:
1. **Thread-Safe & ACID Compliant:** Bookings use transactional synchronization and atomic database constraints to eliminate race conditions.
2. **Standardized Error Responses:** Clear JSON error payloads with HTTP status codes (400, 404, 409) and granular details.
3. **No External Database Setup Required:** In-memory H2 database runs out-of-the-box.
4. **Embedded Maven Wrapper:** Pre-bundled `mvnw` and `mvnw.cmd` allow running on any machine with Java installed without needing global Maven.

---

## 🚀 Quickstart & How to Run

### Prerequisites
- **Java 21 or higher** (`java -version`)

### 1. Start the Backend Engine
Run the provided startup script or maven wrapper:

**On Windows:**
```cmd
.\run.bat
# Or manually:
.\mvnw.cmd spring-boot:run
```

**On Linux / macOS:**
```bash
chmod +x ./run.sh ./mvnw
./run.sh
# Or manually:
./mvnw spring-boot:run
```

Once started, the engine is accessible at:
- **Web UI & Interactive Console:** `http://localhost:8080/`
- **H2 Database Console:** `http://localhost:8080/h2-console` (JDBC URL: `jdbc:h2:mem:meetingroomdb`, User: `sa`, Password: empty)

---

## 🧪 Running Tests & Automated Verification

### Automated End-to-End Curl Test Suite
With the server running on port 8080, run the test script:

**On Windows:**
```cmd
.\test-suite.bat
```

**On Linux / macOS:**
```bash
chmod +x ./test-suite.sh
./test-suite.sh
```

### Unit & Integration Test Suite (JUnit 5 + MockMvc)
```bash
./mvnw test
```

---

## 📡 API Reference & cURL Examples

### 1. M1: Create a Booking
**Endpoint:** `POST /api/bookings`

**Request:**
```bash
curl -X POST http://localhost:8080/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": "ROOM-102",
    "title": "Sprint Planning",
    "organiser": "alice@example.com",
    "startTime": "2026-11-02T09:00:00",
    "endTime": "2026-11-02T10:00:00",
    "attendees": ["alice@example.com", "bob@example.com"]
  }'
```

**Response (201 Created):**
```json
{
  "id": "BKG-7A2F1B09",
  "roomId": "ROOM-102",
  "title": "Sprint Planning",
  "organiser": "alice@example.com",
  "startTime": "2026-11-02T09:00:00",
  "endTime": "2026-11-02T10:00:00",
  "attendees": ["alice@example.com", "bob@example.com"],
  "attendeeCount": 2,
  "createdAt": "2026-10-27T11:00:00",
  "updatedAt": "2026-10-27T11:00:00"
}
```

---

### 2. M2: Overlap Conflict Rejection
**Endpoint:** `POST /api/bookings`

If a booking overlaps (e.g. `09:30:00` to `10:30:00` on `ROOM-102`):

**Response (409 Conflict):**
```json
{
  "timestamp": "2026-10-27T11:05:00",
  "status": 409,
  "error": "Conflict",
  "code": "BOOKING_CONFLICT",
  "message": "Room 'ROOM-102' is already booked from 2026-11-02T09:00 to 2026-11-02T10:00 by alice@example.com (Booking ID: BKG-7A2F1B09)",
  "path": "/api/bookings",
  "details": {
    "conflictingBookingId": "BKG-7A2F1B09",
    "conflictingOrganiser": "alice@example.com"
  }
}
```

---

### 3. M2: Back-to-Back Bookings (Allowed)
**Endpoint:** `POST /api/bookings`

Booking immediately after an existing booking (`10:00:00` to `11:00:00` on `ROOM-102`) succeeds with **201 Created**.

---

### 4. M3: Capacity Exceeded Rejection
**Endpoint:** `POST /api/bookings`

`ROOM-PHONE-1` has a max capacity of 2. Attempting to book with 4 attendees:

**Response (400 Bad Request):**
```json
{
  "timestamp": "2026-10-27T11:08:00",
  "status": 400,
  "error": "Bad Request",
  "code": "CAPACITY_EXCEEDED",
  "message": "Room 'ROOM-PHONE-1' has capacity 2, but 4 attendees were requested",
  "path": "/api/bookings",
  "details": {
    "roomId": "ROOM-PHONE-1",
    "requestedAttendees": 4,
    "roomCapacity": 2
  }
}
```

---

### 5. M4: Find Earliest Slot
**Endpoint:** `GET /api/rooms/find-slot?date=2026-11-02&duration=45&attendees=6`

**Response (200 OK):**
```json
{
  "roomId": "ROOM-102",
  "roomName": "Alan Turing Huddle Room",
  "roomCapacity": 8,
  "startTime": "2026-11-02T10:00:00",
  "endTime": "2026-11-02T10:45:00",
  "durationMinutes": 45,
  "attendeeCount": 6,
  "officeHoursWindow": "09:00 - 18:00"
}
```
*Note: Evaluates only rooms with capacity >= 6, searches within 09:00 to 18:00, and chooses the earliest slot. If multiple rooms are free at that earliest time, chooses the smallest room (cap 8) rather than an oversized boardroom (cap 24).*

---

### 6. M5: Weekly Recurring Bookings with Occurrence Conflict Reporting
**Endpoint:** `POST /api/bookings/recurring`

**Request:**
```bash
curl -X POST http://localhost:8080/api/bookings/recurring \
  -H "Content-Type: application/json" \
  -d '{
    "roomId": "ROOM-102",
    "title": "Weekly Architecture Sync",
    "organiser": "architect@example.com",
    "startTime": "2026-11-02T09:00:00",
    "endTime": "2026-11-02T10:00:00",
    "occurrences": 4,
    "policy": "BOOK_AVAILABLE",
    "attendees": ["dev1@example.com", "dev2@example.com"]
  }'
```

**Response (201 Created):**
```json
{
  "recurrenceGroupId": "REC-7F084939",
  "policy": "BOOK_AVAILABLE",
  "totalRequested": 4,
  "successfulCount": 3,
  "conflictCount": 1,
  "successfulBookings": [
    {
      "id": "BKG-20BD50BC",
      "roomId": "ROOM-102",
      "startTime": "2026-11-09T09:00:00",
      "endTime": "2026-11-09T10:00:00",
      "occurrenceIndex": 2
    },
    {
      "id": "BKG-3A14A1CE",
      "roomId": "ROOM-102",
      "startTime": "2026-11-16T09:00:00",
      "endTime": "2026-11-16T10:00:00",
      "occurrenceIndex": 3
    },
    {
      "id": "BKG-A50F24F8",
      "roomId": "ROOM-102",
      "startTime": "2026-11-23T09:00:00",
      "endTime": "2026-11-23T10:00:00",
      "occurrenceIndex": 4
    }
  ],
  "conflicts": [
    {
      "occurrenceIndex": 1,
      "date": "2026-11-02",
      "startTime": "2026-11-02T09:00:00",
      "endTime": "2026-11-02T10:00:00",
      "reason": "OVERLAP_CONFLICT",
      "message": "Room 'ROOM-102' is already booked by alice@example.com (2026-11-02T09:00 to 2026-11-02T10:00)",
      "conflictingBookingId": "BKG-DBBC29F0",
      "conflictingOrganiser": "alice@example.com"
    }
  ]
}
```

---

## 🛡️ Edge Cases Handled

1. **Zero & Inverted Duration:** Rejects any booking where `startTime >= endTime` with 400 Bad Request.
2. **Back-to-Back Precision:** Half-open interval intersection $[S_1, E_1) \cap [S_2, E_2)$ strictly ensures $E_1 == S_2$ is not an overlap.
3. **Self-Collision on Update:** Updating a booking's title or room preserves safety and does not conflict with its own current slot.
4. **Room Capacity Upper Bound:** Explicitly catches attendee list counts exceeding room limits, returning descriptive error payloads.
5. **Office Hours Boundary:** M4 find-slot strictly constrains slots between `09:00:00` and `18:00:00`. Bookings requiring slots that would spill past 18:00 are rejected.
6. **Best-Fit Space Allocation:** If two rooms are available at 09:00, the algorithm automatically picks the smaller room that satisfies attendee capacity, conserving larger spaces for larger groups.
7. **Atomic vs Best-Effort Recurrence:** Supports `ALL_OR_NOTHING` (rolls back entire recurring batch if any conflict occurs) or `BOOK_AVAILABLE` (saves clear weeks while providing per-occurrence conflict details).

---

## 📁 Sample Rooms Data (`data/rooms.json`)

```json
[
  { "id": "ROOM-101", "name": "Ada Lovelace Focus Room", "capacity": 4, "floor": 1, "amenities": ["WHITEBOARD", "WIFI"] },
  { "id": "ROOM-102", "name": "Alan Turing Huddle Room", "capacity": 8, "floor": 1, "amenities": ["PROJECTOR", "WHITEBOARD", "VIDEO_CONFERENCE"] },
  { "id": "ROOM-201", "name": "Grace Hopper Conference Room", "capacity": 12, "floor": 2, "amenities": ["PROJECTOR", "WHITEBOARD", "VIDEO_CONFERENCE", "DUAL_MONITORS"] },
  { "id": "ROOM-301", "name": "Margaret Hamilton Boardroom", "capacity": 24, "floor": 3, "amenities": ["4K_DISPLAY", "VIDEO_CONFERENCE", "WHITEBOARD", "PODIUM", "MIC_SYSTEM"] },
  { "id": "ROOM-PHONE-1", "name": "Claude Shannon Phone Booth", "capacity": 2, "floor": 1, "amenities": ["ACOUSTIC_PANEL", "MONITOR"] }
]
```
