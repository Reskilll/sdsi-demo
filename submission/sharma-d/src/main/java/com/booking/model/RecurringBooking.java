package com.booking.model;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

public class RecurringBooking {
    private String id;
    private String roomId;
    private String organiser;
    private LocalDate startDate; // when recurrence begins
    private LocalDate endDate;   // when recurrence ends (inclusive)
    private LocalTime start;
    private LocalTime end;
    private List<String> attendees;

    public RecurringBooking() {}

    public RecurringBooking(String id, String roomId, String organiser, LocalDate startDate,
                            LocalDate endDate, LocalTime start, LocalTime end,
                            List<String> attendees) {
        this.id = id;
        this.roomId = roomId;
        this.organiser = organiser;
        this.startDate = startDate;
        this.endDate = endDate;
        this.start = start;
        this.end = end;
        this.attendees = attendees;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getRoomId() { return roomId; }
    public void setRoomId(String roomId) { this.roomId = roomId; }

    public String getOrganiser() { return organiser; }
    public void setOrganiser(String organiser) { this.organiser = organiser; }

    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }

    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }

    public LocalTime getStart() { return start; }
    public void setStart(LocalTime start) { this.start = start; }

    public LocalTime getEnd() { return end; }
    public void setEnd(LocalTime end) { this.end = end; }

    public List<String> getAttendees() { return attendees; }
    public void setAttendees(List<String> attendees) { this.attendees = attendees; }
}