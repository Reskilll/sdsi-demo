package com.sdsi.booking.web.dto;

import java.time.LocalDateTime;
import java.util.UUID;

public record ConflictView(
        UUID bookingId,
        String title,
        String organiser,
        LocalDateTime start,
        LocalDateTime end) {
}
