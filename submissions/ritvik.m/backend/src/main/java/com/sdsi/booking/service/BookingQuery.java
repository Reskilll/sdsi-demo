package com.sdsi.booking.service;

import com.sdsi.booking.domain.BookingStatus;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

public record BookingQuery(
        String roomId,
        String organiser,
        BookingStatus status,
        UUID seriesId,
        LocalDate date,
        LocalDateTime from,
        LocalDateTime to,
        int page,
        int size) {
}
