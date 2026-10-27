package com.reskilll.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;

public class FindSlotRequest {

    @NotNull(message = "Date is required")
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate date;

    @NotNull(message = "Duration in minutes is required")
    @Min(value = 1, message = "Duration must be at least 1 minute")
    @Max(value = 540, message = "Duration cannot exceed 540 minutes (9 hours office day)")
    private Integer durationMinutes;

    @NotNull(message = "Attendee count is required")
    @Min(value = 1, message = "Attendee count must be at least 1")
    private Integer attendeeCount;

    public FindSlotRequest() {
    }

    public FindSlotRequest(LocalDate date, Integer durationMinutes, Integer attendeeCount) {
        this.date = date;
        this.durationMinutes = durationMinutes;
        this.attendeeCount = attendeeCount;
    }

    public LocalDate getDate() {
        return date;
    }

    public void setDate(LocalDate date) {
        this.date = date;
    }

    public Integer getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(Integer durationMinutes) {
        this.durationMinutes = durationMinutes;
    }

    public Integer getAttendeeCount() {
        return attendeeCount;
    }

    public void setAttendeeCount(Integer attendeeCount) {
        this.attendeeCount = attendeeCount;
    }
}
