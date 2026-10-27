package com.sdsi.booking.service;

import com.sdsi.booking.web.error.RuleViolationException;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.TreeSet;

public final class RecurrenceGenerator {

    public static final int MAX_OCCURRENCES = 366;

    private RecurrenceGenerator() {
    }

    /**
     * Returns every matching weekday inside the {@code weeks}-long window that
     * starts on the Monday of the week containing {@code startsOn}. Dates before
     * {@code startsOn} are skipped. The result is chronologically ordered and
     * contains no duplicates.
     */
    public static List<LocalDate> occurrenceDates(LocalDate startsOn, int weeks,
                                                  Collection<DayOfWeek> daysOfWeek) {
        if (startsOn == null) {
            throw new RuleViolationException("INVALID_RECURRENCE", "startsOn is required.");
        }
        if (weeks < 1 || weeks > 52) {
            throw new RuleViolationException("INVALID_RECURRENCE", "weeks must be between 1 and 52.");
        }
        if (daysOfWeek == null || daysOfWeek.isEmpty()) {
            throw new RuleViolationException("INVALID_RECURRENCE", "Select at least one weekday.");
        }

        TreeSet<DayOfWeek> days = new TreeSet<>(daysOfWeek);
        LocalDate windowStart = startsOn.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
        List<LocalDate> dates = new ArrayList<>();

        for (int week = 0; week < weeks; week++) {
            LocalDate monday = windowStart.plusWeeks(week);
            for (DayOfWeek day : days) {
                LocalDate date = monday.plusDays(day.getValue() - 1L);
                if (!date.isBefore(startsOn)) {
                    dates.add(date);
                }
            }
        }

        if (dates.isEmpty()) {
            throw new RuleViolationException("NO_OCCURRENCES",
                    "The recurrence does not produce any occurrence; check startsOn, weeks and daysOfWeek.");
        }
        if (dates.size() > MAX_OCCURRENCES) {
            throw new RuleViolationException("TOO_MANY_OCCURRENCES",
                    "A series may contain at most " + MAX_OCCURRENCES + " occurrences.");
        }
        return List.copyOf(dates);
    }
}
