package com.sdsi.booking.service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Pure interval arithmetic, kept separate from persistence so the edge cases
 * (touching intervals, overlapping data, out-of-hours bookings) are easy to
 * test.
 */
public final class FreeWindows {

    private FreeWindows() {
    }

    /**
     * Clips busy ranges to [open, close), merges them and returns the gaps.
     * Half-open ranges mean 10:00-11:00 and 11:00-12:00 leave no gap and both
     * are fully busy.
     */
    public static List<TimeRange> compute(LocalDateTime open, LocalDateTime close,
                                          List<TimeRange> busyRanges) {
        if (!close.isAfter(open)) {
            return List.of();
        }
        List<TimeRange> clipped = busyRanges.stream()
                .map(range -> new TimeRange(latest(range.start(), open), earliest(range.end(), close)))
                .filter(range -> range.start().isBefore(range.end()))
                .sorted(Comparator.comparing(TimeRange::start))
                .toList();

        List<TimeRange> free = new ArrayList<>();
        LocalDateTime cursor = open;
        for (TimeRange range : clipped) {
            if (range.start().isAfter(cursor)) {
                free.add(new TimeRange(cursor, range.start()));
            }
            if (range.end().isAfter(cursor)) {
                cursor = range.end();
            }
        }
        if (cursor.isBefore(close)) {
            free.add(new TimeRange(cursor, close));
        }
        return free;
    }

    public static LocalDateTime latest(LocalDateTime a, LocalDateTime b) {
        return a.isAfter(b) ? a : b;
    }

    public static LocalDateTime earliest(LocalDateTime a, LocalDateTime b) {
        return a.isBefore(b) ? a : b;
    }
}
