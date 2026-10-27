package com.sdsi.booking.web.dto;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public record SeriesResponse(
        UUID id,
        RoomResponse room,
        String organiser,
        String organiserEmail,
        String title,
        String description,
        LocalTime startTime,
        LocalTime endTime,
        LocalDate startsOn,
        int weeks,
        List<java.time.DayOfWeek> daysOfWeek,
        int attendeeCount,
        Set<String> attendees,
        Instant createdAt,
        List<BookingResponse> occurrences) {
}
