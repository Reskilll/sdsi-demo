package com.booking.model;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

public class Booking {
    private String id;
    private String roomId;
    private String organiser;
    private LocalDate date;
    private LocalTime start;
    private LocalTime end;
    private List<String> attendees;
    private String recurrenceId; // non-null for recurring booking instances

    public Booking() {}

    public Booking(String id, String roomId, String organiser, LocalDate date,
                   LocalTime start, LocalTime end, List<String> attendees) {
        this.id = id;
        this.roomId = roomId;
        this.organiser = organiser;
        this.date = date;
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

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }

    public LocalTime getStart() { return start; }
    public void setStart(LocalTime start) { this.start = start; }

    public LocalTime getEnd() { return end; }
    public void setEnd(LocalTime end) { this.end = end; }

    public List<String> getAttendees() { return attendees; }
    public void setAttendees(List<String> attendees) { this.attendees = attendees; }

    public String getRecurrenceId() { return recurrenceId; }
    public void setRecurrenceId(String recurrenceId) { this.recurrenceId = recurrenceId; }

    @Override
    public String toString() {
        return "Booking{id='" + id + "', roomId='" + roomId + "', organiser='" + organiser
                + "', date=" + date + ", start=" + start + ", end=" + end
                + ", attendees=" + attendees + "}";
    }
}