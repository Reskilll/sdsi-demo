package com.sdsi.booking.web.dto;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;

public record RecurringPreviewResponse(
        LocalDate startsOn,
        int weeks,
        List<DayOfWeek> daysOfWeek,
        int occurrenceCount,
        int conflictCount,
        List<OccurrenceView> occurrences) {
}
