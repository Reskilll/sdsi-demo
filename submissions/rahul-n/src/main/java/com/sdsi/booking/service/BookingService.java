package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.web.dto.BookingDtos;
import com.sdsi.booking.web.error.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;

/**
 * M1–M3: create, read, update, delete meetings with overlap and capacity enforcement.
 *
 * <p>Every mutating path opens a transaction, takes the room's pessimistic write lock,
 * and only then evaluates overlaps. Holding the lock across check-and-insert is what
 * makes concurrent double-booking impossible.
 *
 * <p>All instants are normalised to UTC on the way in and on the way out, so two callers
 * describing the same moment with different offsets (09:00Z and 14:30+05:30) collide
 * instead of slipping past each other.
 */
@Service
public class BookingService {

    private final RoomRepository rooms;
    private final BookingRepository bookings;

    public BookingService(RoomRepository rooms, BookingRepository bookings) {
        this.rooms = rooms;
        this.bookings = bookings;
    }

    @Transactional
    public BookingDtos.BookingResponse create(BookingDtos.BookingRequest request) {
        Room room = lockRoom(request.roomId());
        OffsetDateTime start = normalise(request.startTime());
        OffsetDateTime end = normalise(request.endTime());
        List<String> attendees = AttendeeRules.normalise(request.attendees());
        validateWindow(start, end);
        validateCapacity(room, attendees.size());
        assertNoOverlap(room, start, end, null);

        Booking saved = bookings.save(new Booking(room, organiserOf(request), start, end, attendees));
        return BookingDtos.BookingResponse.from(saved);
    }

    @Transactional
    public BookingDtos.BookingResponse reschedule(Long id, BookingDtos.BookingRequest request) {
        Booking booking = bookings.findById(id)
                .orElseThrow(() -> new ApiException.NotFound("booking %d not found".formatted(id)));
        Room room = lockRoom(request.roomId());
        OffsetDateTime start = normalise(request.startTime());
        OffsetDateTime end = normalise(request.endTime());
        List<String> attendees = AttendeeRules.normalise(request.attendees());
        validateWindow(start, end);
        validateCapacity(room, attendees.size());
        assertNoOverlap(room, start, end, id);

        booking.reschedule(room, organiserOf(request), start, end, attendees);
        return BookingDtos.BookingResponse.from(bookings.save(booking));
    }

    private static String organiserOf(BookingDtos.BookingRequest request) {
        if (request.organiser() == null || request.organiser().isBlank()) {
            throw new ApiException.BadRequest("organiser is required");
        }
        return request.organiser().trim();
    }

    @Transactional(readOnly = true)
    public BookingDtos.BookingResponse get(Long id) {
        return bookings.findById(id)
                .map(BookingDtos.BookingResponse::from)
                .orElseThrow(() -> new ApiException.NotFound("booking %d not found".formatted(id)));
    }

    @Transactional(readOnly = true)
    public List<BookingDtos.BookingResponse> list(Long roomId) {
        List<Booking> found = roomId == null
                ? bookings.findAll()
                : bookings.findByRoom_IdOrderByStartTimeAsc(roomId);
        return found.stream().map(BookingDtos.BookingResponse::from).toList();
    }

    @Transactional
    public void delete(Long id) {
        Booking booking = bookings.findById(id)
                .orElseThrow(() -> new ApiException.NotFound("booking %d not found".formatted(id)));
        bookings.delete(booking);
    }

    @Transactional(readOnly = true)
    public List<BookingDtos.RoomResponse> listRooms() {
        return rooms.findAllByOrderByCapacityAscIdAsc().stream()
                .map(BookingDtos.RoomResponse::from)
                .toList();
    }

    // ---------------------------------------------------------------- internals

    private Room lockRoom(Long roomId) {
        if (roomId == null) {
            throw new ApiException.BadRequest("roomId is required");
        }
        return rooms.findByIdForUpdate(roomId)
                .orElseThrow(() -> new ApiException.NotFound("room %d not found".formatted(roomId)));
    }

    /** Bean validation does not run for programmatic callers, so nulls are checked here. */
    private void validateWindow(OffsetDateTime start, OffsetDateTime end) {
        if (start == null || end == null) {
            throw new ApiException.BadRequest("startTime and endTime are required");
        }
        if (!end.isAfter(start)) {
            throw new ApiException.BadRequest("endTime must be strictly after startTime");
        }
        if (start.isBefore(OffsetDateTime.now(ZoneOffset.UTC))) {
            throw new ApiException.BadRequest("startTime must not be in the past");
        }
        if (!BusinessHours.isWithinWorkingHours(start, end)) {
            throw new ApiException.BadRequest(
                    "booking must fall inside 09:00-18:00 UTC on a single weekday");
        }
    }

    /** M3 — capacity violation is a 400 with the numbers spelled out. */
    private void validateCapacity(Room room, int attendeeCount) {
        if (attendeeCount > room.getCapacity()) {
            throw new ApiException.CapacityExceeded(
                    "attendees (%d) exceed %s capacity (%d)".formatted(attendeeCount, room.getName(), room.getCapacity()));
        }
    }

    /** M2 — half-open overlap test; {@code ignoreId} excludes the booking being rescheduled. */
    private void assertNoOverlap(Room room, OffsetDateTime start, OffsetDateTime end, Long ignoreId) {
        List<Booking> conflicts = bookings.findOverlapping(room.getId(), start, end).stream()
                .filter(b -> ignoreId == null || !b.getId().equals(ignoreId))
                .toList();
        if (!conflicts.isEmpty()) {
            List<String> details = conflicts.stream()
                    .map(b -> "%s-%s (%s)".formatted(b.getStartTime(), b.getEndTime(), b.getOrganiser()))
                    .toList();
            throw new ApiException.Conflict(
                    "%s is already booked during the requested window".formatted(room.getName()), details);
        }
    }

    /** Stored instants are always UTC, so comparisons never depend on the client's offset. */
    private static OffsetDateTime normalise(OffsetDateTime instant) {
        if (instant == null) {
            throw new ApiException.BadRequest("startTime and endTime are required");
        }
        return instant.withOffsetSameInstant(ZoneOffset.UTC);
    }
}
