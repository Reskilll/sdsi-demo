package com.sdsi.booking.service;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class FreeWindowsTest {

    private final LocalDate day = LocalDate.of(2026, 11, 2);
    private final LocalDateTime open = day.atTime(9, 0);
    private final LocalDateTime close = day.atTime(18, 0);

    @Test
    void noBusyMeansOneFullWindow() {
        assertThat(FreeWindows.compute(open, close, List.of()))
                .containsExactly(new TimeRange(open, close));
    }

    @Test
    void busyInTheMiddleSplitsTheDay() {
        List<TimeRange> free = FreeWindows.compute(open, close,
                List.of(new TimeRange(day.atTime(10, 0), day.atTime(11, 0))));
        assertThat(free).containsExactly(
                new TimeRange(open, day.atTime(10, 0)),
                new TimeRange(day.atTime(11, 0), close));
    }

    @Test
    void touchingBusyRangesAreMergedWithoutAPhantomGap() {
        List<TimeRange> free = FreeWindows.compute(open, close, List.of(
                new TimeRange(day.atTime(10, 0), day.atTime(11, 0)),
                new TimeRange(day.atTime(11, 0), day.atTime(12, 0))));
        assertThat(free).containsExactly(
                new TimeRange(open, day.atTime(10, 0)),
                new TimeRange(day.atTime(12, 0), close));
    }

    @Test
    void overlappingAndUnsortedRangesAreMerged() {
        List<TimeRange> free = FreeWindows.compute(open, close, List.of(
                new TimeRange(day.atTime(11, 0), day.atTime(13, 0)),
                new TimeRange(day.atTime(10, 0), day.atTime(12, 0))));
        assertThat(free).containsExactly(
                new TimeRange(open, day.atTime(10, 0)),
                new TimeRange(day.atTime(13, 0), close));
    }

    @Test
    void rangesOutsideTheDayAreClipped() {
        List<TimeRange> free = FreeWindows.compute(open, close, List.of(
                new TimeRange(day.atTime(8, 0), day.atTime(9, 30)),
                new TimeRange(day.atTime(17, 30), day.atTime(19, 0))));
        assertThat(free).containsExactly(new TimeRange(day.atTime(9, 30), day.atTime(17, 30)));
    }

    @Test
    void fullyBusyDayHasNoFreeWindow() {
        assertThat(FreeWindows.compute(open, close,
                List.of(new TimeRange(day.atTime(8, 0), day.atTime(20, 0))))).isEmpty();
    }

    @Test
    void zeroLengthRangesAreIgnored() {
        assertThat(FreeWindows.compute(open, close,
                List.of(new TimeRange(day.atTime(10, 0), day.atTime(10, 0)))))
                .containsExactly(new TimeRange(open, close));
    }

    @Test
    void invalidDayWindowReturnsNoWindows() {
        assertThat(FreeWindows.compute(close, open, List.of())).isEmpty();
    }
}
