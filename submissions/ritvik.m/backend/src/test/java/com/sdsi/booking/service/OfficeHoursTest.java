package com.sdsi.booking.service;

import com.sdsi.booking.config.AppProperties;
import com.sdsi.booking.web.error.RuleViolationException;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class OfficeHoursTest {

    private final OfficeHours hours = new OfficeHours(properties());

    @Test
    void acceptsWindowInsideOfficeHours() {
        assertThatCode(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 9, 0),
                LocalDateTime.of(2026, 11, 2, 18, 0))).doesNotThrowAnyException();

        assertThatCode(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 9, 15),
                LocalDateTime.of(2026, 11, 2, 9, 30))).doesNotThrowAnyException();
    }

    @Test
    void rejectsStartBeforeOpeningAndEndAfterClosing() {
        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 8, 59),
                LocalDateTime.of(2026, 11, 2, 10, 0)))
                .extracting("code").isEqualTo("OUTSIDE_OFFICE_HOURS");

        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 17, 0),
                LocalDateTime.of(2026, 11, 2, 18, 0, 1)))
                .extracting("code").isEqualTo("OUTSIDE_OFFICE_HOURS");
    }

    @Test
    void rejectsReversedOrZeroLengthIntervals() {
        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 11, 0),
                LocalDateTime.of(2026, 11, 2, 10, 0)))
                .extracting("code").isEqualTo("INVALID_INTERVAL");

        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 11, 0),
                LocalDateTime.of(2026, 11, 2, 11, 0)))
                .extracting("code").isEqualTo("INVALID_INTERVAL");
    }

    @Test
    void rejectsOvernightBookings() {
        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 17, 0),
                LocalDateTime.of(2026, 11, 3, 1, 0)))
                .isInstanceOf(RuleViolationException.class)
                .extracting("code").isEqualTo("INVALID_INTERVAL");
    }

    @Test
    void enforcesMinimumDuration() {
        assertThatThrownBy(() -> hours.validateWindow(
                LocalDateTime.of(2026, 11, 2, 10, 0),
                LocalDateTime.of(2026, 11, 2, 10, 10)))
                .extracting("code").isEqualTo("INVALID_DURATION");
    }

    @Test
    void exposesConfiguredBounds() {
        org.assertj.core.api.Assertions.assertThat(hours.getMaxDurationMinutes()).isEqualTo(540);
        org.assertj.core.api.Assertions.assertThat(hours.openOn(java.time.LocalDate.of(2026, 11, 2)))
                .isEqualTo(LocalDateTime.of(2026, 11, 2, 9, 0));
    }

    static AppProperties properties() {
        return new AppProperties(
                new AppProperties.Office("Europe/London", java.time.LocalTime.of(9, 0),
                        java.time.LocalTime.of(18, 0), 15, 15, 100),
                new AppProperties.Security(true, "test", "test", "ADMIN"),
                new AppProperties.Cors(List.of("http://localhost:5173")),
                new AppProperties.Seed("classpath:rooms.json"));
    }
}
