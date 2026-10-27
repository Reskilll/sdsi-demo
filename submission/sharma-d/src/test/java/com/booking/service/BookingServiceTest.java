package com.booking.service;

import com.booking.model.Booking;
import org.junit.jupiter.api.Test;

import java.time.LocalTime;

import static org.junit.jupiter.api.Assertions.*;

class BookingServiceTest {

    @Test
    void overlaps_overlapping() {
        assertTrue(BookingService.overlaps(
                LocalTime.of(10, 0), LocalTime.of(11, 0),
                LocalTime.of(10, 30), LocalTime.of(12, 0)));
    }

    @Test
    void overlaps_backToBackAllowed() {
        // 10:00-11:00 and 11:00-12:00 on same room — allowed
        assertFalse(BookingService.overlaps(
                LocalTime.of(10, 0), LocalTime.of(11, 0),
                LocalTime.of(11, 0), LocalTime.of(12, 0)));
    }

    @Test
    void overlaps_noOverlap() {
        assertFalse(BookingService.overlaps(
                LocalTime.of(9, 0), LocalTime.of(10, 0),
                LocalTime.of(10, 30), LocalTime.of(11, 0)));
    }

    @Test
    void overlaps_firstTouchesSecondBackToBack() {
        // 13:00-14:00 and 12:00-13:00 — BAck-to-back (allowed)
        assertFalse(BookingService.overlaps(
                LocalTime.of(13, 0), LocalTime.of(14, 0),
                LocalTime.of(12, 0), LocalTime.of(13, 0)));
    }
}