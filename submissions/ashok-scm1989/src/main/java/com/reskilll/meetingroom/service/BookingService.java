package com.reskilll.meetingroom.service;

import com.reskilll.meetingroom.dto.*;
import com.reskilll.meetingroom.exception.BookingConflictException;
import com.reskilll.meetingroom.exception.InvalidBookingException;
import com.reskilll.meetingroom.exception.ResourceNotFoundException;
import com.reskilll.meetingroom.model.Booking;
import com.reskilll.meetingroom.model.RecurrencePolicy;
import com.reskilll.meetingroom.model.Room;
import com.reskilll.meetingroom.repository.BookingRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional
public class BookingService {

    private static final Logger log = LoggerFactory.getLogger(BookingService.class);

    private final BookingRepository bookingRepository;
    private final RoomService roomService;

    @Value("${app.office-hours.start:09:00}")
    private String officeHoursStartStr;

    @Value("${app.office-hours.end:18:00}")
    private String officeHoursEndStr;

    public BookingService(BookingRepository bookingRepository, RoomService roomService) {
        this.bookingRepository = bookingRepository;
        this.roomService = roomService;
    }

    /**
     * M1 & M2 & M3: Create a booking with overlap checking and capacity validation.
     */
    public synchronized BookingResponse createBooking(CreateBookingRequest request) {
        validateBookingTimes(request.getStartTime(), request.getEndTime());

        String normalisedRoomId = request.getRoomId().trim().toUpperCase();
        Room room = roomService.getRoomById(normalisedRoomId);

        // M3: Capacity check
        int attendeesCount = request.getAttendees() != null ? request.getAttendees().size() : 0;
        if (attendeesCount == 0) {
            throw new InvalidBookingException("Attendees list cannot be empty");
        }
        roomService.validateCapacity(room.getId(), attendeesCount);

        // M2: Overlap check
        checkOverlap(room.getId(), request.getStartTime(), request.getEndTime(), null);

        String id = generateBookingId();
        Booking booking = new Booking(
                id,
                room.getId(),
                request.getTitle(),
                request.getOrganiser().trim(),
                request.getStartTime(),
                request.getEndTime(),
                request.getAttendees(),
                null,
                null
        );

        Booking saved = bookingRepository.save(booking);
        log.info("Created booking [{}] in room '{}' for organiser '{}' ({} to {})",
                saved.getId(), saved.getRoomId(), saved.getOrganiser(), saved.getStartTime(), saved.getEndTime());
        return BookingResponse.fromEntity(saved);
    }

    /**
     * M1: Read booking by ID.
     */
    @Transactional(readOnly = true)
    public BookingResponse getBooking(String id) {
        Booking booking = findBookingEntity(id);
        return BookingResponse.fromEntity(booking);
    }

    /**
     * M1: List bookings with optional filters.
     */
    @Transactional(readOnly = true)
    public List<BookingResponse> listBookings(String roomId, String organiser, LocalDate date) {
        List<Booking> list;

        if (roomId != null && !roomId.isBlank()) {
            list = bookingRepository.findByRoomIdOrderByStartTimeAsc(roomId.trim().toUpperCase());
        } else if (organiser != null && !organiser.isBlank()) {
            list = bookingRepository.findByOrganiserOrderByStartTimeAsc(organiser.trim());
        } else if (date != null) {
            LocalDateTime dayStart = date.atStartOfDay();
            LocalDateTime dayEnd = date.plusDays(1).atStartOfDay();
            list = bookingRepository.findByStartTimeBetweenOrderByStartTimeAsc(dayStart, dayEnd);
        } else {
            list = bookingRepository.findAll().stream()
                    .sorted(Comparator.comparing(Booking::getStartTime))
                    .collect(Collectors.toList());
        }

        // Apply secondary filters in-memory if multiple params passed
        return list.stream()
                .filter(b -> roomId == null || roomId.isBlank() || b.getRoomId().equalsIgnoreCase(roomId.trim()))
                .filter(b -> organiser == null || organiser.isBlank() || b.getOrganiser().equalsIgnoreCase(organiser.trim()))
                .filter(b -> date == null || b.getStartTime().toLocalDate().equals(date))
                .map(BookingResponse::fromEntity)
                .collect(Collectors.toList());
    }

    /**
     * M1 & M2 & M3: Update existing booking.
     */
    public synchronized BookingResponse updateBooking(String id, UpdateBookingRequest request) {
        Booking existing = findBookingEntity(id);

        String newRoomId = request.getRoomId() != null && !request.getRoomId().isBlank()
                ? request.getRoomId().trim().toUpperCase()
                : existing.getRoomId();

        LocalDateTime newStart = request.getStartTime() != null ? request.getStartTime() : existing.getStartTime();
        LocalDateTime newEnd = request.getEndTime() != null ? request.getEndTime() : existing.getEndTime();
        List<String> newAttendees = request.getAttendees() != null ? request.getAttendees() : existing.getAttendees();
        String newTitle = request.getTitle() != null ? request.getTitle() : existing.getTitle();
        String newOrganiser = request.getOrganiser() != null && !request.getOrganiser().isBlank()
                ? request.getOrganiser().trim()
                : existing.getOrganiser();

        validateBookingTimes(newStart, newEnd);

        // M3: Capacity check
        Room room = roomService.getRoomById(newRoomId);
        if (newAttendees == null || newAttendees.isEmpty()) {
            throw new InvalidBookingException("Attendees list cannot be empty");
        }
        roomService.validateCapacity(room.getId(), newAttendees.size());

        // M2: Overlap check excluding this booking itself!
        checkOverlap(room.getId(), newStart, newEnd, existing.getId());

        existing.setRoomId(room.getId());
        existing.setTitle(newTitle);
        existing.setOrganiser(newOrganiser);
        existing.setStartTime(newStart);
        existing.setEndTime(newEnd);
        existing.setAttendees(newAttendees);

        Booking updated = bookingRepository.save(existing);
        log.info("Updated booking [{}] in room '{}' ({} to {})", updated.getId(), updated.getRoomId(), updated.getStartTime(), updated.getEndTime());
        return BookingResponse.fromEntity(updated);
    }

    /**
     * M1: Delete booking by ID.
     */
    public void deleteBooking(String id) {
        Booking booking = findBookingEntity(id);
        bookingRepository.delete(booking);
        log.info("Deleted booking [{}] from room '{}'", booking.getId(), booking.getRoomId());
    }

    /**
     * M4: Find-slot.
     * Given duration (minutes), attendee count, and date:
     * Returns earliest free room and time between 09:00 and 18:00.
     */
    @Transactional(readOnly = true)
    public SlotRecommendation findEarliestSlot(LocalDate date, int durationMinutes, int attendeeCount) {
        if (date == null) {
            throw new InvalidBookingException("Date is required");
        }
        if (durationMinutes <= 0) {
            throw new InvalidBookingException("Duration must be strictly positive");
        }
        if (durationMinutes > 540) {
            throw new InvalidBookingException("Duration cannot exceed 540 minutes (full 09:00-18:00 window)");
        }
        if (attendeeCount <= 0) {
            throw new InvalidBookingException("Attendee count must be strictly positive");
        }

        LocalTime openTime = LocalTime.parse(officeHoursStartStr, DateTimeFormatter.ofPattern("HH:mm"));
        LocalTime closeTime = LocalTime.parse(officeHoursEndStr, DateTimeFormatter.ofPattern("HH:mm"));

        LocalDateTime windowStart = date.atTime(openTime);
        LocalDateTime windowEnd = date.atTime(closeTime);

        // Find candidate rooms with capacity >= attendeeCount
        List<Room> eligibleRooms = roomService.getEligibleRooms(attendeeCount);
        if (eligibleRooms.isEmpty()) {
            throw new ResourceNotFoundException(
                    String.format("No room available with capacity for %d attendees.", attendeeCount));
        }

        List<CandidateSlot> candidateSlots = new ArrayList<>();

        for (Room room : eligibleRooms) {
            List<Booking> bookings = bookingRepository.findBookingsInWindow(room.getId(), windowStart, windowEnd);

            // Find earliest candidate slot within this room
            LocalDateTime cursor = windowStart;

            for (Booking b : bookings) {
                LocalDateTime bStart = b.getStartTime().isBefore(windowStart) ? windowStart : b.getStartTime();
                LocalDateTime bEnd = b.getEndTime().isAfter(windowEnd) ? windowEnd : b.getEndTime();

                if (bStart.isAfter(cursor)) {
                    long gapMinutes = Duration.between(cursor, bStart).toMinutes();
                    if (gapMinutes >= durationMinutes) {
                        candidateSlots.add(new CandidateSlot(room, cursor, cursor.plusMinutes(durationMinutes)));
                        break; // Found earliest slot for this room
                    }
                }

                if (bEnd.isAfter(cursor)) {
                    cursor = bEnd;
                }
            }

            // Check gap between last booking and windowEnd
            if (candidateSlots.stream().noneMatch(c -> c.room.getId().equals(room.getId()))) {
                if (cursor.isBefore(windowEnd)) {
                    long remainingMinutes = Duration.between(cursor, windowEnd).toMinutes();
                    if (remainingMinutes >= durationMinutes) {
                        candidateSlots.add(new CandidateSlot(room, cursor, cursor.plusMinutes(durationMinutes)));
                    }
                }
            }
        }

        if (candidateSlots.isEmpty()) {
            throw new ResourceNotFoundException(String.format(
                    "No available slot found for %d attendees with duration %dm on %s between %s and %s.",
                    attendeeCount, durationMinutes, date, officeHoursStartStr, officeHoursEndStr));
        }

        // Sort candidates:
        // 1. Earliest start time first
        // 2. Best-fit capacity (smallest room that fits the group) to avoid wasting large boardrooms
        // 3. Room ID alphabetically
        candidateSlots.sort(Comparator
                .comparing((CandidateSlot c) -> c.startTime)
                .thenComparingInt(c -> c.room.getCapacity())
                .thenComparing(c -> c.room.getId()));

        CandidateSlot best = candidateSlots.get(0);
        return new SlotRecommendation(
                best.room.getId(),
                best.room.getName(),
                best.room.getCapacity(),
                best.startTime,
                best.endTime,
                durationMinutes,
                attendeeCount
        );
    }

    /**
     * M5: Weekly recurring bookings, reporting conflicts per occurrence.
     */
    public synchronized RecurringBookingResult createRecurringBooking(RecurringBookingRequest request) {
        validateBookingTimes(request.getStartTime(), request.getEndTime());

        String roomId = request.getRoomId().trim().toUpperCase();
        Room room = roomService.getRoomById(roomId);

        int attendeeCount = request.getAttendees() != null ? request.getAttendees().size() : 0;
        if (attendeeCount == 0) {
            throw new InvalidBookingException("Attendees list cannot be empty");
        }
        roomService.validateCapacity(room.getId(), attendeeCount);

        int occurrences = request.getOccurrences() > 0 ? request.getOccurrences() : 4;
        RecurrencePolicy policy = request.getPolicy() != null ? request.getPolicy() : RecurrencePolicy.BOOK_AVAILABLE;

        String recurrenceGroupId = "REC-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();

        List<Booking> candidateBookings = new ArrayList<>();
        List<OccurrenceConflict> conflicts = new ArrayList<>();

        for (int i = 0; i < occurrences; i++) {
            int occurrenceIndex = i + 1;
            LocalDateTime occStart = request.getStartTime().plusWeeks(i);
            LocalDateTime occEnd = request.getEndTime().plusWeeks(i);

            // Check overlap with database bookings
            List<Booking> dbConflicts = bookingRepository.findConflictingBookings(roomId, occStart, occEnd, null);

            // Check overlap with previous occurrences within this recurring series
            boolean intraBatchConflict = candidateBookings.stream().anyMatch(b ->
                    b.getStartTime().isBefore(occEnd) && b.getEndTime().isAfter(occStart));

            if (!dbConflicts.isEmpty()) {
                Booking clash = dbConflicts.get(0);
                conflicts.add(new OccurrenceConflict(
                        occurrenceIndex,
                        occStart.toLocalDate(),
                        occStart,
                        occEnd,
                        "OVERLAP_CONFLICT",
                        String.format("Room '%s' is already booked by %s (%s to %s)",
                                roomId, clash.getOrganiser(), clash.getStartTime(), clash.getEndTime()),
                        clash.getId(),
                        clash.getOrganiser()
                ));
            } else if (intraBatchConflict) {
                conflicts.add(new OccurrenceConflict(
                        occurrenceIndex,
                        occStart.toLocalDate(),
                        occStart,
                        occEnd,
                        "INTRA_BATCH_OVERLAP",
                        "Occurrence conflicts with another booking in the same recurring batch",
                        null,
                        request.getOrganiser()
                ));
            } else {
                Booking b = new Booking(
                        generateBookingId(),
                        roomId,
                        request.getTitle(),
                        request.getOrganiser().trim(),
                        occStart,
                        occEnd,
                        request.getAttendees(),
                        recurrenceGroupId,
                        occurrenceIndex
                );
                candidateBookings.add(b);
            }
        }

        List<BookingResponse> savedResponses = new ArrayList<>();

        if (policy == RecurrencePolicy.ALL_OR_NOTHING && !conflicts.isEmpty()) {
            log.info("Recurring booking [{}] aborted under ALL_OR_NOTHING policy due to {} conflicts",
                    recurrenceGroupId, conflicts.size());
            // Persist nothing
        } else {
            List<Booking> savedList = bookingRepository.saveAll(candidateBookings);
            savedResponses = savedList.stream()
                    .map(BookingResponse::fromEntity)
                    .collect(Collectors.toList());
            log.info("Recurring booking [{}] completed: {} booked, {} conflicts",
                    recurrenceGroupId, savedResponses.size(), conflicts.size());
        }

        return new RecurringBookingResult(
                recurrenceGroupId,
                policy,
                occurrences,
                savedResponses.size(),
                conflicts.size(),
                savedResponses,
                conflicts
        );
    }

    /**
     * Delete entire recurring group by recurrenceGroupId.
     */
    public long deleteRecurringGroup(String recurrenceGroupId) {
        long deleted = bookingRepository.deleteByRecurrenceGroupId(recurrenceGroupId);
        log.info("Deleted {} bookings belonging to recurring group [{}]", deleted, recurrenceGroupId);
        return deleted;
    }

    // Helper methods

    private Booking findBookingEntity(String id) {
        if (id == null || id.isBlank()) {
            throw new ResourceNotFoundException("Booking ID cannot be blank");
        }
        return bookingRepository.findById(id.trim())
                .orElseThrow(() -> new ResourceNotFoundException("Booking not found with ID: " + id));
    }

    private void validateBookingTimes(LocalDateTime start, LocalDateTime end) {
        if (start == null || end == null) {
            throw new InvalidBookingException("Start time and end time are required");
        }
        if (!start.isBefore(end)) {
            throw new InvalidBookingException("Start time must be strictly before end time");
        }
        if (Duration.between(start, end).toMinutes() < 1) {
            throw new InvalidBookingException("Booking duration must be at least 1 minute");
        }
    }

    /**
     * M2: Reject overlapping bookings on the same room. Back-to-back bookings allowed.
     */
    private void checkOverlap(String roomId, LocalDateTime start, LocalDateTime end, String excludeId) {
        List<Booking> conflicts = bookingRepository.findConflictingBookings(roomId, start, end, excludeId);
        if (!conflicts.isEmpty()) {
            Booking c = conflicts.get(0);
            throw new BookingConflictException(
                    String.format("Room '%s' is already booked from %s to %s by %s (Booking ID: %s)",
                            roomId, c.getStartTime(), c.getEndTime(), c.getOrganiser(), c.getId()),
                    c.getId(),
                    c.getOrganiser()
            );
        }
    }

    private String generateBookingId() {
        return "BKG-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }

    private static class CandidateSlot {
        final Room room;
        final LocalDateTime startTime;
        final LocalDateTime endTime;

        CandidateSlot(Room room, LocalDateTime startTime, LocalDateTime endTime) {
            this.room = room;
            this.startTime = startTime;
            this.endTime = endTime;
        }
    }
}
