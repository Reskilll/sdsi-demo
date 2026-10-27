package com.sdsi.booking.service;

import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;

/**
 * Operating window for the booking engine: 09:00–18:00 UTC, Monday to Friday.
 *
 * <p>All instants are normalised to UTC, so "09:00" is unambiguous and does not shift
 * with the caller's zone or DST.
 */
public final class BusinessHours {

    public static final ZoneOffset ZONE = ZoneOffset.UTC;
    public static final LocalTime OPEN = LocalTime.of(9, 0);
    public static final LocalTime CLOSE = LocalTime.of(18, 0);
    public static final ChronoUnit GRANULARITY = ChronoUnit.MINUTES;

    private BusinessHours() {
    }

    /** A booking must sit inside 09:00–18:00 UTC on a weekday. */
    public static boolean isWithinWorkingHours(OffsetDateTime start, OffsetDateTime end) {
        OffsetDateTime s = start.withOffsetSameInstant(ZONE);
        OffsetDateTime e = end.withOffsetSameInstant(ZONE);
        if (!s.toLocalDate().equals(e.toLocalDate())) {
            return false;
        }
        if (isWeekend(s)) {
            return false;
        }
        return !s.toLocalTime().isBefore(OPEN) && !e.toLocalTime().isAfter(CLOSE);
    }

    public static boolean isWeekend(OffsetDateTime instant) {
        return switch (instant.withOffsetSameInstant(ZONE).getDayOfWeek()) {
            case SATURDAY, SUNDAY -> true;
            default -> false;
        };
    }

    public static OffsetDateTime at(LocalTime time, OffsetDateTime day) {
        return day.withOffsetSameInstant(ZONE).toLocalDate().atTime(time).atOffset(ZONE);
    }

    public static long minutesBetween(OffsetDateTime start, OffsetDateTime end) {
        return GRANULARITY.between(start, end);
    }
}
