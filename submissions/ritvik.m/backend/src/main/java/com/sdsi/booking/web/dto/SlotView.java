package com.sdsi.booking.web.dto;

import java.time.LocalDateTime;

public record SlotView(LocalDateTime start, LocalDateTime end, RoomResponse room) {
}
