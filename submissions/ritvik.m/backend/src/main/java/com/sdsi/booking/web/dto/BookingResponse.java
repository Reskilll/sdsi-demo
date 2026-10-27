package com.sdsi.booking.web.dto;

import com.sdsi.booking.domain.BookingStatus;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Set;
import java.util.UUID;

public record BookingResponse(
        UUID id,
        RoomResponse room,
        String organiser,
        String organiserEmail,
        String title,
        String description,
        LocalDateTime start,
        LocalDateTime end,
        int attendeeCount,
        Set<String> attendees,
        BookingStatus status,
        UUID seriesId,
        Integer occurrenceIndex,
        Instant createdAt,
        Instant updatedAt,
        long version) {
}
