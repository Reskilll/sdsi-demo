package com.sdsi.booking.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(
        name = "bookings",
        indexes = @Index(name = "ix_booking_room_window", columnList = "room_id, start_time, end_time")
)
public class Booking {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "room_id", nullable = false)
    private Room room;

    @Column(name = "organiser", nullable = false, length = 128)
    private String organiser;

    /** Half-open interval [startTime, endTime) in UTC. */
    @Column(name = "start_time", nullable = false)
    private OffsetDateTime startTime;

    /** Exclusive end of the half-open interval. */
    @Column(name = "end_time", nullable = false)
    private OffsetDateTime endTime;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "booking_attendees", joinColumns = @JoinColumn(name = "booking_id"))
    @OrderColumn(name = "attendee_order")
    @Column(name = "attendee", nullable = false, length = 128)
    private List<String> attendees = new ArrayList<>();

    protected Booking() {
    }

    public Booking(Room room, String organiser, OffsetDateTime startTime, OffsetDateTime endTime, List<String> attendees) {
        this.room = room;
        this.organiser = organiser;
        this.startTime = startTime;
        this.endTime = endTime;
        this.attendees = new ArrayList<>(attendees);
    }

    public Long getId() {
        return id;
    }

    public Room getRoom() {
        return room;
    }

    public Long getRoomId() {
        return room.getId();
    }

    public String getOrganiser() {
        return organiser;
    }

    public OffsetDateTime getStartTime() {
        return startTime;
    }

    public OffsetDateTime getEndTime() {
        return endTime;
    }

    public List<String> getAttendees() {
        return attendees;
    }

    /** Re-points this booking; callers must have re-validated window, capacity and overlap. */
    public void reschedule(Room room, String organiser, OffsetDateTime startTime, OffsetDateTime endTime,
                           List<String> attendees) {
        this.room = room;
        this.organiser = organiser;
        this.startTime = startTime;
        this.endTime = endTime;
        this.attendees = new ArrayList<>(attendees);
    }

    /** True when this booking shares any instant with [start, end). */
    public boolean overlaps(OffsetDateTime start, OffsetDateTime end) {
        return startTime.isBefore(end) && endTime.isAfter(start);
    }
}
