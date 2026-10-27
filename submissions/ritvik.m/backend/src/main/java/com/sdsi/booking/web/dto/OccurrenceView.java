package com.sdsi.booking.web.dto;

import java.time.LocalDateTime;
import java.util.List;

/**
 * One prospective recurrence occurrence and, if it clashes, the bookings it
 * clashes with. Used by both the preview and the create response.
 */
public record OccurrenceView(
        LocalDateTime start,
        LocalDateTime end,
        OccurrenceStatus status,
        List<ConflictView> conflicts) {
}
