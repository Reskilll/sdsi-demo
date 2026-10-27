package com.sdsi.booking.service;

import com.sdsi.booking.web.error.RuleViolationException;
import org.junit.jupiter.api.Test;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RecurrenceGeneratorTest {

    @Test
    void defaultsToWeeklyOccurrences() {
        LocalDate monday = LocalDate.of(2026, 11, 2);
        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(monday, 3, Set.of(DayOfWeek.MONDAY));
        assertThat(dates).containsExactly(monday, monday.plusWeeks(1), monday.plusWeeks(2));
    }

    @Test
    void skipsDaysBeforeStartsOnInsideTheFirstWeek() {
        LocalDate wednesday = LocalDate.of(2026, 11, 4);
        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(wednesday, 2,
                Set.of(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY));
        assertThat(dates).containsExactly(
                wednesday,
                wednesday.plusWeeks(1).minusDays(2),
                wednesday.plusWeeks(1));
    }

    @Test
    void generatesNothingWhenAllDaysPrecedeStartsOnInTheWindow() {
        LocalDate sunday = LocalDate.of(2026, 11, 8);
        assertThatThrownBy(() -> RecurrenceGenerator.occurrenceDates(sunday, 1, Set.of(DayOfWeek.MONDAY)))
                .isInstanceOf(RuleViolationException.class)
                .extracting("code").isEqualTo("NO_OCCURRENCES");
    }

    @Test
    void duplicateDaysAreDeduplicated() {
        LocalDate monday = LocalDate.of(2026, 11, 2);
        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(monday, 1,
                List.of(DayOfWeek.MONDAY, DayOfWeek.MONDAY));
        assertThat(dates).containsExactly(monday);
    }

    @Test
    void crossingAYearBoundaryWorks() {
        LocalDate monday = LocalDate.of(2026, 12, 28);
        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(monday, 2, Set.of(DayOfWeek.FRIDAY));
        assertThat(dates).containsExactly(LocalDate.of(2027, 1, 1), LocalDate.of(2027, 1, 8));
    }

    @Test
    void fiftyTwoWeeksOfSevenDaysIsAllowed() {
        LocalDate monday = LocalDate.of(2026, 11, 2);
        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(monday, 52, Set.of(DayOfWeek.values()));
        assertThat(dates).hasSize(364);
    }

    @Test
    void invalidInputsAreRejected() {
        LocalDate monday = LocalDate.of(2026, 11, 2);
        assertThatThrownBy(() -> RecurrenceGenerator.occurrenceDates(monday, 0, Set.of(DayOfWeek.MONDAY)))
                .isInstanceOf(RuleViolationException.class);
        assertThatThrownBy(() -> RecurrenceGenerator.occurrenceDates(monday, 53, Set.of(DayOfWeek.MONDAY)))
                .isInstanceOf(RuleViolationException.class);
        assertThatThrownBy(() -> RecurrenceGenerator.occurrenceDates(monday, 1, Set.of()))
                .isInstanceOf(RuleViolationException.class);
    }
}
