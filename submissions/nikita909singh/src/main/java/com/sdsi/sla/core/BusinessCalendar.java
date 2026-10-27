package com.sdsi.sla.core;

import com.sdsi.sla.model.SlaPolicy;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.Set;

/**
 * Business-time arithmetic: working days (default Mon–Fri) between {@code dayStart} and {@code dayEnd}
 * (default 09:00–18:00) in the policy's time zone, minus holidays (M1, M2).
 *
 * <p>Works in seconds internally and walks day by day, so the cost is O(calendar days spanned): a ticket
 * open for a whole year needs about 365 cheap steps. Each day's window is built with
 * {@code LocalDate.atTime(...).atZone(zone)}, so daylight-saving changes are handled by java.time.
 */
public final class BusinessCalendar {

    /** Stops runaway searches, e.g. a policy whose holidays cover every working day. */
    static final int MAX_SEARCH_DAYS = 3_660;

    private final ZoneId zone;
    private final Set<DayOfWeek> workDays;
    private final LocalTime dayStart;
    private final LocalTime dayEnd;
    private final Set<LocalDate> holidays;

    public BusinessCalendar(SlaPolicy policy, Set<LocalDate> holidays) {
        this.zone = policy.zone();
        this.workDays = Set.copyOf(policy.workDays());
        this.dayStart = policy.dayStart();
        this.dayEnd = policy.dayEnd();
        this.holidays = Set.copyOf(holidays);
        if (workDays.isEmpty()) {
            throw new ValidationException("the policy must have at least one working day");
        }
        if (!dayStart.isBefore(dayEnd)) {
            throw new ValidationException("business hours must start before they end (same day)");
        }
    }

    public ZoneId zone() {
        return zone;
    }

    public boolean isBusinessDay(LocalDate date) {
        return workDays.contains(date.getDayOfWeek()) && !holidays.contains(date);
    }

    /** Business seconds in [from, to). Zero when {@code to} is not after {@code from}. */
    public long businessSeconds(Instant from, Instant to) {
        if (!to.isAfter(from)) {
            return 0;
        }
        LocalDate day = from.atZone(zone).toLocalDate();
        LocalDate last = to.atZone(zone).toLocalDate();
        long total = 0;
        for (; !day.isAfter(last); day = day.plusDays(1)) {
            if (!isBusinessDay(day)) {
                continue;
            }
            Instant open = windowStart(day);
            Instant close = windowEnd(day);
            Instant a = from.isAfter(open) ? from : open;
            Instant b = to.isBefore(close) ? to : close;
            if (b.isAfter(a)) {
                total += b.getEpochSecond() - a.getEpochSecond();
            }
        }
        return total;
    }

    /**
     * The instant at which {@code seconds} of business time have passed after {@code from}. If the
     * amount runs out exactly at closing time, the answer is closing time (18:00), not the next
     * morning.
     */
    public Instant addBusinessSeconds(Instant from, long seconds) {
        if (seconds < 0) {
            throw new IllegalArgumentException("seconds must not be negative");
        }
        if (seconds == 0) {
            return from; // even outside business hours: nothing to add, so nothing moves
        }
        LocalDate day = from.atZone(zone).toLocalDate();
        long remaining = seconds;
        for (int i = 0; i < MAX_SEARCH_DAYS; i++, day = day.plusDays(1)) {
            if (!isBusinessDay(day)) {
                continue;
            }
            Instant open = windowStart(day);
            Instant close = windowEnd(day);
            Instant start = from.isAfter(open) ? from : open;
            if (!close.isAfter(start)) {
                continue;
            }
            long available = close.getEpochSecond() - start.getEpochSecond();
            if (remaining <= available) {
                return start.plusSeconds(remaining);
            }
            remaining -= available;
        }
        throw new ValidationException("no business time found within " + MAX_SEARCH_DAYS
                + " days; check the working days and holidays");
    }

    private Instant windowStart(LocalDate day) {
        return day.atTime(dayStart).atZone(zone).toInstant();
    }

    private Instant windowEnd(LocalDate day) {
        return day.atTime(dayEnd).atZone(zone).toInstant();
    }
}
