package com.sdsi.booking.web.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Create payload. Either {@code attendeeCount} or {@code attendees} may be
 * supplied; if both are present they must describe the same number of people.
 */
public record BookingCreateRequest(
        @NotBlank @Size(max = 40) String roomId,
        @NotBlank @Size(max = 120) String organiser,
        @Email @Size(max = 160) String organiserEmail,
        @NotBlank @Size(max = 160) String title,
        @Size(max = 1000) String description,
        @NotNull LocalDateTime start,
        @NotNull LocalDateTime end,
        @Min(1) @Max(1000) Integer attendeeCount,
        @Size(max = 50) List<@NotBlank @Size(max = 120) String> attendees) {
}
