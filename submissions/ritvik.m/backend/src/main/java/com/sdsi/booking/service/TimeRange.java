package com.sdsi.booking.service;

import java.time.LocalDateTime;

public record TimeRange(LocalDateTime start, LocalDateTime end) {

    public boolean overlaps(LocalDateTime otherStart, LocalDateTime otherEnd) {
        return otherStart.isBefore(end) && otherEnd.isAfter(start);
    }
}
