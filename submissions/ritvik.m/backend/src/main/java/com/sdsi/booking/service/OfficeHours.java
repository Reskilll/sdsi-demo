package com.sdsi.booking.service;

import com.sdsi.booking.config.AppProperties;
import com.sdsi.booking.web.error.RuleViolationException;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;

/**
 * Single source of truth for opening hours and booking interval rules.
 */
@Component
public class OfficeHours {

    private final LocalTime opensAt;
    private final LocalTime closesAt;
    private final int minDurationMinutes;

    public OfficeHours(AppProperties properties) {
        this.opensAt = properties.office().opensAt();
        this.closesAt = properties.office().closesAt();
        this.minDurationMinutes = properties.office().minDurationMinutes();
        if (!closesAt.isAfter(opensAt)) {
            throw new IllegalStateException("app.office.closes-at must be after app.office.opens-at");
        }
    }

    public void validateWindow(LocalDateTime start, LocalDateTime end) {
        if (!end.isAfter(start)) {
            throw new RuleViolationException("INVALID_INTERVAL", "The end time must be after the start time.");
        }
        if (!start.toLocalDate().equals(end.toLocalDate())) {
            throw new RuleViolationException("INVALID_INTERVAL",
                    "A booking must start and end on the same day.");
        }
        long minutes = Duration.between(start, end).toMinutes();
        if (minutes < minDurationMinutes) {
            throw new RuleViolationException("INVALID_DURATION",
                    "A booking must last at least " + minDurationMinutes + " minutes.");
        }
        if (start.toLocalTime().isBefore(opensAt) || end.toLocalTime().isAfter(closesAt)) {
            throw new RuleViolationException("OUTSIDE_OFFICE_HOURS",
                    "Bookings must be between " + opensAt + " and " + closesAt + " (office time).");
        }
        if (start.getSecond() != 0 || start.getNano() != 0
                || end.getSecond() != 0 || end.getNano() != 0) {
            throw new RuleViolationException("INVALID_INTERVAL",
                    "Times must use whole minutes (seconds must be zero).");
        }
    }

    public LocalDateTime openOn(LocalDate date) {
        return date.atTime(opensAt);
    }

    public LocalDateTime closeOn(LocalDate date) {
        return date.atTime(closesAt);
    }

    public LocalTime getOpensAt() {
        return opensAt;
    }

    public LocalTime getClosesAt() {
        return closesAt;
    }

    public int getMinDurationMinutes() {
        return minDurationMinutes;
    }

    public int getMaxDurationMinutes() {
        return (int) Duration.between(opensAt, closesAt).toMinutes();
    }
}
