package com.sdsi.booking.web.dto;

import java.time.LocalDateTime;

public record FreeInterval(LocalDateTime start, LocalDateTime end, long minutes) {
}
