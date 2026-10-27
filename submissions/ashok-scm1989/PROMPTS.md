# AI Collaboration Log (PROMPTS.md)

> **Competition:** SDSI Agentic AI Hackathon — Round 1 Developer Screening Round  
> **Problem Statement:** PS2 Meeting Room Booking Engine Backend  
> **Participant / Alias:** Ashok (`ashok-scm1989`)  
> **Stack:** Java 21, Spring Boot 3.3.5, Spring Data JPA, H2 In-Memory Database, Maven  

---

## 1. Collaboration Workflow Overview

This document details the iterative AI pair-programming process used to design, implement, test, and document the solution for **PS2: Meeting Room Booking Engine**.

```
[Requirement Analysis] ➔ [Domain Modeling] ➔ [Core Logic Implementation] ➔ [API & Web UI Layer] ➔ [Verification & Test Automation]
```

---

## 2. Prompt History & Progression

### Step 1: Requirements Breakdown & Technology Selection
- **Objective:** Extract the exact core milestones (M1–M5), non-functional requirements, edge cases, and submission protocol.
- **Architectural Decision:** Selected **Java 21 with Spring Boot 3** because of strong type safety, declarative transaction management (`@Transactional`), clean JPA repository abstractions, and enterprise-grade validation.
- **Milestones Identified:**
  - `M1`: CRUD Bookings (room, organiser, start, end, attendees).
  - `M2`: Reject overlapping bookings on same room ($S_1 < E_2 \land E_1 > S_2$), strictly allow back-to-back ($E_1 == S_2$).
  - `M3`: Capacity enforcement from `rooms.json` seed data.
  - `M4`: Find-slot search algorithm between 09:00 and 18:00 with earliest slot and best-fit room capacity tie-breaking.
  - `M5`: Weekly recurring bookings with per-occurrence conflict analysis.

---

### Step 2: Domain Modeling & Data Contracts
- **Prompts & Queries:**
  - "Design domain entities for Room and Booking with half-open interval overlap math."
  - "How should recurrence conflict reporting be structured so clients can inspect individual weeks?"
- **Decisions:**
  - Standardized timestamps on ISO-8601 (`LocalDateTime`).
  - Added `RecurrencePolicy` (`BOOK_AVAILABLE` vs `ALL_OR_NOTHING`).
  - Implemented `OccurrenceConflict` DTO returning `occurrenceIndex`, `date`, `startTime`, `endTime`, `conflictingBookingId`, and `conflictingOrganiser`.

---

### Step 3: Core Algorithm Implementation

#### Overlap Check (M2)
Implemented standard interval collision query in Spring Data JPA:
```sql
SELECT b FROM Booking b WHERE b.roomId = :roomId
  AND b.startTime < :endTime AND b.endTime > :startTime
  AND (:excludeBookingId IS NULL OR b.id <> :excludeBookingId)
```
- Back-to-back bookings: When $b.endTime == startTime$ or $b.startTime == endTime$, the condition $b.startTime < endTime \land b.endTime > startTime$ evaluates to `false`, naturally allowing back-to-back bookings with zero special-casing hacks.
- Exclude booking ID on update: Ensures that updating a meeting's attendees or description does not flag a false conflict against itself.

#### Find-Slot Algorithm (M4)
- Filter candidate rooms by `capacity >= attendeeCount`.
- For each room, examine booked intervals on that date clamped to the `09:00 - 18:00` window.
- Search for the first gap with duration $\ge$ `requestedDuration`.
- Multi-criteria tie-breaker:
  1. Earliest slot start time.
  2. Best-fit capacity (closest capacity to attendee count) to preserve large boardrooms.
  3. Room ID alphabetically for deterministic results.

---

### Step 4: Robust Exception Handling & REST Contracts
- Built `GlobalExceptionHandler` mapping domain exceptions to standard HTTP status codes:
  - `BookingConflictException` ➔ `409 Conflict`
  - `CapacityExceededException` ➔ `400 Bad Request`
  - `ResourceNotFoundException` ➔ `404 Not Found`
  - `InvalidBookingException` ➔ `400 Bad Request`
  - `MethodArgumentNotValidException` ➔ `400 Bad Request` with field-level errors

---

### Step 5: Verification & Automated Test Suites
- Created automated test scripts (`test-suite.bat` and `test-suite.sh`) executing live curl requests covering:
  - M1: Booking creation & retrieval
  - M2: Overlap conflict rejection (409)
  - M2: Back-to-back booking validation (201)
  - M3: Capacity exceeded rejection (400)
  - M4: Find-slot with 45m duration and 6 attendees
  - M5: Weekly recurring with conflict reporting per occurrence
- Built unit test suite with 25+ assertions testing boundary conditions.

---

### Step 6: Interactive Web UI (Stretch Goal)
- Implemented a single-page responsive dashboard at `/` (served via `index.html`).
- Features:
  - Instant demo trigger buttons for evaluators.
  - Interactive "Find Earliest Slot" search bar with 1-click booking.
  - Recurring schedule simulator with green/red status per occurrence.
  - Seeded room catalog visualization from `rooms.json`.

---

## 3. Review Checklist Against Evaluation Criteria

- [x] **M1 CRUD:** Full support for Create, Read, Update, Delete with filtering.
- [x] **M2 Overlap Detection:** Mathematical interval collision checking with back-to-back support.
- [x] **M3 Capacity Check:** Rejection when attendee count > room capacity, loaded from `rooms.json`.
- [x] **M4 Find-Slot Engine:** Office-hours constraint (09:00 - 18:00), earliest slot discovery, best-fit tie breaker.
- [x] **M5 Weekly Recurrence:** Multi-occurrence projection, per-week conflict reporting, group deletion.
- [x] **Testing:** Automated curl test suite + JUnit 5 tests.
- [x] **Documentation & Runnability:** Full `README.md` with step-by-step setup and curl snippets.
- [x] **AI Collaboration Effectiveness:** Transparent documentation of prompts and rationale in `PROMPTS.md`.
- [x] **Edge Cases Handled:** Inverted times, zero duration, self-collision on update, capacity boundary equality.
- [x] **Bonus / Stretch:** Modern Web UI dashboard + Standalone Maven wrapper.
