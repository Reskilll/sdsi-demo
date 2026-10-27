# AI Collaboration Log

## 1. Project Setup

**Prompt**: "Create a Spring Boot project for a meeting room booking backend at `submission/sharma-d/` with Maven. Scaffold the standard package structure: model, dto, repository, service, controller, exception, config."

**AI resolution**: Created `pom.xml` with `spring-boot-starter-web` and `spring-boot-starter-validation`, plus the directory tree and `MeetingRoomBookingApplication.java`.

## 2. Domain Model

**Prompt**: "Design the Java records/classes: Room (id, name, capacity), Booking (id, roomId, organiser, date, start, end, attendees, recurrenceId nullable), RecurringBooking (id, roomId, organiser, startDate, endDate, start, end, attendees). Use POJOs for mutability on Booking since it gets updated."

**AI resolution**: Created `Room` as a record (immutable), `Booking` as a mutable POJO, `RecurringBooking` as a POJO. All in `com.booking.model`.

## 3. DTO Layer

**Prompt**: "Create request/response DTOs: BookingRequest with Jakarta validation, FindSlotRequest, RecurringBookingRequest, RecurringBookingResponse (with ConflictDetail inner class), FindSlotResponse, and ApiError."

**AI resolution**: Created all DTOs with `@NotBlank`, `@NotNull`, `@Size`, `@Positive`, `@Min` annotations.

## 4. Repository

**Prompt**: "Build an in-memory BookingRepository using ConcurrentHashMap. It should store bookings and rooms. Add methods: findById, findAll, save, deleteById, findByRoomAndDate, findByDate, addRoom, findRoomById, findAllRooms, findRoomsByMinCapacity."

**AI resolution**: Single `@Repository` class with two `ConcurrentHashMap` maps. Thread-safe, no persistence.

## 5. Business Logic (M2 + M3 overlap & capacity)

**Prompt**: "Implement BookingService.createBooking with: (a) validate times within 09:00-18:00, (b) reject if end ≤ start, (c) look up room and reject if attendees > capacity, (d) fetch existing bookings for same room+date, (e) reject if any overlap where overlap = s1 < e2 AND s2 < e1 (this allows back-to-back). Similarly for updateBooking."

**AI resolution**: The `overlaps` static method uses `s1.isBefore(e2) && s2.isBefore(e1)` — this correctly rejects true overlaps while allowing back-to-back (e.g., 10:00–11:00 and 11:00–12:00).

## 6. Find Slot (M4)

**Prompt**: "Implement find-slot: given duration, attendee count, and date, find the earliest available room+time across all rooms with enough capacity, scanning 09:00–18:00. Sort rooms by capacity ascending. For each room, build a list of busy intervals from existing bookings, then scan for the first gap wide enough."

**AI resolution**: Used a private `TimeSlot` record implementing `Comparable`. Iterates rooms sorted by capacity; for each room, walks through its busy intervals pushing a cursor forward to find the first gap that fits the duration.

## 7. Recurring Bookings (M5)

**Prompt**: "Implement weekly recurring bookings. Given startDate, endDate, time range, and attendees, create one Booking per week. Check conflicts per occurrence; report successful vs conflicting dates separately. Store the recurrenceId on each instance."

**AI resolution**: Loops `cursor = startDate; cursor <= endDate; cursor = cursor.plusWeeks(1)`. For each date, checks overlap against existing bookings for that room+date. Partial success: creates non-conflicting instances, reports conflicting ones with reasons.

## 8. Controller & Exception Handling

**Prompt**: "Wire up BookingController with REST endpoints and GlobalExceptionHandler mapping custom exceptions to HTTP status codes."

**AI resolution**: Controller at `/api/bookings` with 7 endpoints. `@RestControllerAdvice` maps: `BookingConflictException → 409`, `CapacityExceededException → 422`, `NotFoundException → 404`, validation/illegal-arg → 400.

## 9. Testing

**Prompt**: "Write integration tests with MockMvc covering all M1-M5 criteria plus edge cases: missing fields, invalid times, out-of-hours, unknown room/booking."

**AI resolution**: 18 tests in `BookingControllerTest` + 4 unit tests for the overlap logic in `BookingServiceTest`.

## 10. Documentation

**Prompt**: "Write README.md with API reference, error table, design decisions, and run/test instructions. Write PROMPTS.md capturing the collaboration log."

**AI resolution**: Created both files with full detail.

---

## Key Design Decisions Made with AI

1. **Overlap formula**: `s1 < e2 && s2 < e1` — discussed and agreed this correctly allows back-to-back.
2. **Recurring strategy**: Weekly fixed. Partial-success model chosen over all-or-nothing.
3. **Find-slot**: Scan all rooms, not just first-fit. Return best (earliest) across rooms.
4. **422 for capacity**: Chose `UNPROCESSABLE_ENTITY` over `400` to distinguish capacity from validation.
5. **In-memory**: No persistence needed for the scope; `ConcurrentHashMap` for thread safety.