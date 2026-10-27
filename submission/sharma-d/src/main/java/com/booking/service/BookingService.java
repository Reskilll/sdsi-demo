package com.booking.service;

import com.booking.dto.*;
import com.booking.dto.RecurringBookingResponse.ConflictDetail;
import com.booking.exception.*;
import com.booking.model.Booking;
import com.booking.model.RecurringBooking;
import com.booking.model.Room;
import com.booking.repository.BookingRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Service
public class BookingService {

    private static final LocalTime BUSINESS_START = LocalTime.of(9, 0);
    private static final LocalTime BUSINESS_END = LocalTime.of(18, 0);

    private final BookingRepository repo;

    public BookingService(BookingRepository repo) {
        this.repo = repo;
        // Load sample rooms
        repo.addRoom(new Room("r1", "Atlas", 4));
        repo.addRoom(new Room("r2", "Boardroom", 8));
        repo.addRoom(new Room("r3", "Conference-A", 12));
        repo.addRoom(new Room("r4", "Conference-B", 20));
        repo.addRoom(new Room("r5", "Town Hall", 50));
    }

    public Booking createBooking(BookingRequest req) {
        validateTimes(req.getStart(), req.getEnd());
        Room room = getRoom(req.getRoomId());
        validateCapacity(room, req.getAttendees().size());

        List<Booking> existing = repo.findByRoomAndDate(req.getRoomId(), req.getDate());
        checkOverlap(existing, null, req.getStart(), req.getEnd());

        Booking b = new Booking(UUID.randomUUID().toString(),
                req.getRoomId(), req.getOrganiser(), req.getDate(),
                req.getStart(), req.getEnd(), req.getAttendees());
        return repo.save(b);
    }

    public Booking getBooking(String id) {
        return repo.findById(id)
                .orElseThrow(() -> new BookingNotFoundException("Booking not found: " + id));
    }

    public List<Booking> getAllBookings() {
        return repo.findAll();
    }

    public Booking updateBooking(String id, BookingRequest req) {
        validateTimes(req.getStart(), req.getEnd());
        Booking existing = getBooking(id);
        Room room = getRoom(req.getRoomId());
        validateCapacity(room, req.getAttendees().size());

        List<Booking> sameRoom = repo.findByRoomAndDate(req.getRoomId(), req.getDate());
        checkOverlap(sameRoom, id, req.getStart(), req.getEnd());

        existing.setRoomId(req.getRoomId());
        existing.setOrganiser(req.getOrganiser());
        existing.setDate(req.getDate());
        existing.setStart(req.getStart());
        existing.setEnd(req.getEnd());
        existing.setAttendees(req.getAttendees());
        return repo.save(existing);
    }

    public void deleteBooking(String id) {
        getBooking(id); // throws if not found
        repo.deleteById(id);
    }

    // --- M4: Find slot ---

    public FindSlotResponse findSlot(FindSlotRequest req) {
        LocalDate date = req.getDate();
        int duration = req.getDurationMinutes();
        int needed = req.getAttendeeCount();

        List<Room> suitableRooms = repo.findRoomsByMinCapacity(needed);
        if (suitableRooms.isEmpty()) {
            return new FindSlotResponse(false, null, null, date.toString(), null);
        }

        // For each room, find earliest free slot
        FindSlotResponse best = null;

        for (Room room : suitableRooms) {
            List<Booking> bookings = repo.findByRoomAndDate(room.id(), date);
            List<TimeSlot> busy = bookings.stream()
                    .map(b -> new TimeSlot(b.getStart(), b.getEnd()))
                    .sorted()
                    .toList();

            LocalTime start = BUSINESS_START;
            LocalTime earliestEnd = start.plusMinutes(duration);

            if (earliestEnd.isAfter(BUSINESS_END)) continue;

            for (TimeSlot ts : busy) {
                if (!start.isBefore(ts.start)) {
                    // start is inside or after this busy slot
                    if (start.isBefore(ts.end)) {
                        start = ts.end; // push past it
                        earliestEnd = start.plusMinutes(duration);
                    }
                    continue;
                }
                // start is before this busy slot
                // check if we can fit the meeting before the busy slot
                LocalTime candidateEnd = start.plusMinutes(duration);
                if (!candidateEnd.isAfter(ts.start) && !candidateEnd.isAfter(BUSINESS_END)) {
                    break; // fits — use this start
                }
                // doesn't fit before — push past
                start = ts.end;
                earliestEnd = start.plusMinutes(duration);
            }

            if (earliestEnd.isAfter(BUSINESS_END)) continue;

            if (best == null || start.isBefore(LocalTime.parse(best.getStartTime()))) {
                best = new FindSlotResponse(true, room.id(), room.name(),
                        date.toString(), start.toString());
            }
        }

        return best != null ? best : new FindSlotResponse(false, null, null, date.toString(), null);
    }

    // --- M5: Recurring bookings ---

    public RecurringBookingResponse createRecurring(RecurringBookingRequest req) {
        validateTimes(req.getStart(), req.getEnd());
        Room room = getRoom(req.getRoomId());
        validateCapacity(room, req.getAttendees().size());

        if (req.getEndDate().isBefore(req.getStartDate())) {
            throw new IllegalArgumentException("endDate must be >= startDate");
        }

        RecurringBooking rb = new RecurringBooking(UUID.randomUUID().toString(),
                req.getRoomId(), req.getOrganiser(), req.getStartDate(), req.getEndDate(),
                req.getStart(), req.getEnd(), req.getAttendees());

        List<Booking> successful = new ArrayList<>();
        List<ConflictDetail> conflicts = new ArrayList<>();
        String recurrenceId = rb.getId();

        LocalDate cursor = req.getStartDate();
        while (!cursor.isAfter(req.getEndDate())) {
            boolean conflict = false;
            String reason = null;

            List<Booking> existing = repo.findByRoomAndDate(req.getRoomId(), cursor);
            // check overlap
            for (Booking eb : existing) {
                if (overlaps(req.getStart(), req.getEnd(), eb.getStart(), eb.getEnd())) {
                    conflict = true;
                    reason = "Overlaps with existing booking " + eb.getId();
                    break;
                }
            }

            if (!conflict) {
                Booking instance = new Booking(UUID.randomUUID().toString(),
                        req.getRoomId(), req.getOrganiser(), cursor,
                        req.getStart(), req.getEnd(), new ArrayList<>(req.getAttendees()));
                instance.setRecurrenceId(recurrenceId);
                repo.save(instance);
                successful.add(instance);
            } else {
                conflicts.add(new ConflictDetail(cursor.toString(), reason));
            }

            cursor = cursor.plusWeeks(1);
        }

        return new RecurringBookingResponse(rb, successful, conflicts);
    }

    // --- Helpers ---

    private void validateTimes(LocalTime start, LocalTime end) {
        if (!end.isAfter(start)) {
            throw new IllegalArgumentException("end must be after start");
        }
        if (start.isBefore(BUSINESS_START) || end.isAfter(BUSINESS_END)) {
            throw new IllegalArgumentException(
                    "Booking must be within business hours " + BUSINESS_START + " to " + BUSINESS_END);
        }
    }

    private Room getRoom(String roomId) {
        return repo.findRoomById(roomId)
                .orElseThrow(() -> new RoomNotFoundException("Room not found: " + roomId));
    }

    private void validateCapacity(Room room, int attendeeCount) {
        if (attendeeCount > room.capacity()) {
            throw new CapacityExceededException(
                    "Room '" + room.name() + "' capacity is " + room.capacity()
                            + " but booking has " + attendeeCount + " attendees");
        }
    }

    private void checkOverlap(List<Booking> existing, String excludeId,
                              LocalTime start, LocalTime end) {
        for (Booking eb : existing) {
            if (eb.getId().equals(excludeId)) continue;
            if (overlaps(start, end, eb.getStart(), eb.getEnd())) {
                throw new BookingConflictException(
                        "Overlaps with existing booking " + eb.getId()
                                + " (" + eb.getStart() + "-" + eb.getEnd() + ")");
            }
        }
    }

    static boolean overlaps(LocalTime s1, LocalTime e1, LocalTime s2, LocalTime e2) {
        // NOT overlapping if one ends at or before the other starts (back-to-back OK)
        return s1.isBefore(e2) && s2.isBefore(e1);
    }

    // --- Internal time-slot helper ---

    private record TimeSlot(LocalTime start, LocalTime end) implements Comparable<TimeSlot> {
        @Override public int compareTo(TimeSlot o) {
            return this.start.compareTo(o.start);
        }
    }
}