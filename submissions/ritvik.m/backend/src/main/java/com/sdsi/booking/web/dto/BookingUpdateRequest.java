package com.sdsi.booking.web.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Full replacement update. {@code version} is optional; when supplied a stale
 * value is rejected with 409 so concurrent edits are not silently lost.
 */
public record BookingUpdateRequest(
        @NotBlank @Size(max = 40) String roomId,
        @NotBlank @Size(max = 120) String organiser,
        @Email @Size(max = 160) String organiserEmail,
        @NotBlank @Size(max = 160) String title,
        @Size(max = 1000) String description,
        @NotNull LocalDateTime start,
        @NotNull LocalDateTime end,
        @Min(1) @Max(1000) Integer attendeeCount,
        @Size(max = 50) List<@NotBlank @Size(max = 120) String> attendees,
        @PositiveOrZero Long version) {
}
