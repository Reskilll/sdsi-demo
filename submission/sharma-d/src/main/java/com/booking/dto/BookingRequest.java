package com.booking.dto;

import jakarta.validation.constraints.*;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

public class BookingRequest {

    @NotBlank(message = "roomId is required")
    private String roomId;

    @NotBlank(message = "organiser is required")
    private String organiser;

    @NotNull(message = "date is required (yyyy-MM-dd)")
    private LocalDate date;

    @NotNull(message = "start time is required (HH:mm)")
    private LocalTime start;

    @NotNull(message = "end time is required (HH:mm)")
    private LocalTime end;

    @NotNull(message = "attendees list is required")
    @Size(min = 1, message = "at least one attendee required")
    private List<@NotBlank String> attendees;

    public String getRoomId() { return roomId; }
    public void setRoomId(String roomId) { this.roomId = roomId; }

    public String getOrganiser() { return organiser; }
    public void setOrganiser(String organiser) { this.organiser = organiser; }

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }

    public LocalTime getStart() { return start; }
    public void setStart(LocalTime start) { this.start = start; }

    public LocalTime getEnd() { return end; }
    public void setEnd(LocalTime end) { this.end = end; }

    public List<String> getAttendees() { return attendees; }
    public void setAttendees(List<String> attendees) { this.attendees = attendees; }
}