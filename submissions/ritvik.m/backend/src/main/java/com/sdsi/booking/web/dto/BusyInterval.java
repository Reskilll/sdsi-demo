package com.sdsi.booking.web.dto;

import java.time.LocalDateTime;
import java.util.UUID;

public record BusyInterval(
        LocalDateTime start,
        LocalDateTime end,
        UUID bookingId,
        String title,
        String organiser) {
}
