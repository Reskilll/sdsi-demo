package com.booking.dto;

import jakarta.validation.constraints.*;
import java.time.LocalDate;

public class FindSlotRequest {

    @Positive(message = "durationMinutes must be > 0")
    private int durationMinutes;

    @Min(value = 1, message = "attendeeCount must be >= 1")
    private int attendeeCount;

    @NotNull(message = "date is required (yyyy-MM-dd)")
    private LocalDate date;

    public int getDurationMinutes() { return durationMinutes; }
    public void setDurationMinutes(int durationMinutes) { this.durationMinutes = durationMinutes; }

    public int getAttendeeCount() { return attendeeCount; }
    public void setAttendeeCount(int attendeeCount) { this.attendeeCount = attendeeCount; }

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
}