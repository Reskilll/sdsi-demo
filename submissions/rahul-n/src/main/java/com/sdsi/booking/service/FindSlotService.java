package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.web.dto.BookingDtos;
import com.sdsi.booking.web.error.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

/**
 * M4 — earliest compliant window for a group.
 *
 * <p>Rooms are scanned smallest-capacity-first so the first hit is the tightest fit;
 * large rooms stay free for large groups. Within a room the day is swept from 09:00 in
 * {@link BusinessHours#GRANULARITY} steps and the first gap that holds the duration wins.
 */
@Service
public class FindSlotService {

    private final RoomRepository rooms;
    private final BookingRepository bookings;

    public FindSlotService(RoomRepository rooms, BookingRepository bookings) {
        this.rooms = rooms;
        this.bookings = bookings;
    }

    @Transactional(readOnly = true)
    public BookingDtos.SlotSuggestion findSlot(int durationMinutes, int attendeeCount, LocalDate date) {
        if (attendeeCount < 1) {
            throw new ApiException.BadRequest("attendeeCount must be >= 1");
        }
        if (durationMinutes < 1) {
            throw new ApiException.BadRequest("duration must be >= 1 minute");
        }
        if (date == null) {
            throw new ApiException.BadRequest("date is required");
        }
        if (date.isBefore(LocalDate.now(ZoneOffset.UTC))) {
            throw new ApiException.BadRequest("date must be today or in the future");
        }
        OffsetDateTime dayOpen = date.atTime(BusinessHours.OPEN).atOffset(BusinessHours.ZONE);
        if (BusinessHours.isWeekend(dayOpen)) {
            throw new ApiException.NotFound("no availability on %s: the office is closed at weekends".formatted(date));
        }
        OffsetDateTime dayClose = date.atTime(BusinessHours.CLOSE).atOffset(BusinessHours.ZONE);
        if (durationMinutes > BusinessHours.minutesBetween(dayOpen, dayClose)) {
            throw new ApiException.BadRequest(
                    "duration of %d minutes cannot fit inside the working day".formatted(durationMinutes));
        }

        List<Room> candidates = rooms.findAllByOrderByCapacityAscIdAsc().stream()
                .filter(room -> room.getCapacity() >= attendeeCount)
                .toList();
        if (candidates.isEmpty()) {
            throw new ApiException.NotFound(
                    "no room has capacity for %d attendees".formatted(attendeeCount));
        }

        for (Room room : candidates) {
            List<Booking> busy = bookings.findInWindow(room.getId(), dayOpen, dayClose);
            Optional<OffsetDateTime> start = earliestGap(busy, dayOpen, dayClose, durationMinutes);
            if (start.isPresent()) {
                OffsetDateTime end = start.get().plusMinutes(durationMinutes);
                return new BookingDtos.SlotSuggestion(
                        room.getId(), room.getName(), room.getCapacity(), start.get(), end);
            }
        }
        throw new ApiException.NotFound(
                "no room is free for %d minutes on %s".formatted(durationMinutes, date));
    }

    /**
     * Sweeps candidate starts forward, jumping past each conflicting booking rather than
     * stepping minute-by-minute through it.
     */
    private Optional<OffsetDateTime> earliestGap(List<Booking> busy, OffsetDateTime dayOpen,
                                                 OffsetDateTime dayClose, int durationMinutes) {
        OffsetDateTime cursor = dayOpen.withOffsetSameInstant(ZoneOffset.UTC);
        OffsetDateTime close = dayClose.withOffsetSameInstant(ZoneOffset.UTC);
        for (Booking existing : busy) {
            OffsetDateTime occupiedStart = existing.getStartTime().withOffsetSameInstant(ZoneOffset.UTC);
            OffsetDateTime occupiedEnd = existing.getEndTime().withOffsetSameInstant(ZoneOffset.UTC);
            if (!cursor.plusMinutes(durationMinutes).isAfter(occupiedStart)) {
                break;
            }
            if (occupiedEnd.isAfter(cursor)) {
                cursor = occupiedEnd;
            }
        }
        return cursor.plusMinutes(durationMinutes).isAfter(close) ? Optional.empty() : Optional.of(cursor);
    }
}
