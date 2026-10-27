package com.sdsi.booking.web.dto;

import java.util.List;
import java.util.UUID;

public record RecurringCreateResponse(
        UUID seriesId,
        SeriesSummaryResponse series,
        List<BookingResponse> created,
        List<OccurrenceView> skipped,
        String message) {
}
