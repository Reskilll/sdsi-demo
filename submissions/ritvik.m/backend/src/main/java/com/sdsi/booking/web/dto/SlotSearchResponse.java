package com.sdsi.booking.web.dto;

import java.time.LocalDate;
import java.util.List;

/**
 * @param slot         earliest free room/time for the requested duration
 * @param alternatives other rooms' earliest free windows, ordered by start time
 * @param message      human readable explanation when no slot exists
 */
public record SlotSearchResponse(
        LocalDate date,
        int durationMinutes,
        int attendees,
        SlotView slot,
        List<SlotView> alternatives,
        String message) {
}
