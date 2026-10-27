package com.sdsi.booking.web.dto;

import java.time.LocalDate;
import java.util.List;

public record RoomAvailabilityResponse(
        RoomResponse room,
        LocalDate date,
        List<BusyInterval> busy,
        List<FreeInterval> free) {
}
