package com.sdsi.booking.web.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

/**
 * Weekly recurrence definition. Occurrences are generated for every selected
 * weekday inside a window of {@code weeks} weeks starting on the week that
 * contains {@code startsOn}. If {@code daysOfWeek} is omitted the weekday of
 * {@code startsOn} is used.
 */
public record RecurringBookingRequest(
        @NotBlank @Size(max = 40) String roomId,
        @NotBlank @Size(max = 120) String organiser,
        @Email @Size(max = 160) String organiserEmail,
        @NotBlank @Size(max = 160) String title,
        @Size(max = 1000) String description,
        @NotNull LocalDate startsOn,
        @NotNull LocalTime startTime,
        @NotNull LocalTime endTime,
        @Size(max = 7) List<@NotNull DayOfWeek> daysOfWeek,
        @Min(1) @Max(52) int weeks,
        @Min(1) @Max(1000) Integer attendeeCount,
        @Size(max = 50) List<@NotBlank @Size(max = 120) String> attendees,
        boolean skipConflicts) {
}
