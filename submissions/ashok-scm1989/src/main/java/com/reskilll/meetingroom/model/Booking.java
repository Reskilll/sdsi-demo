package com.reskilll.meetingroom.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Entity
@Table(name = "bookings", indexes = {
        @Index(name = "idx_booking_room_time", columnList = "roomId, startTime, endTime"),
        @Index(name = "idx_booking_recurrence", columnList = "recurrenceGroupId")
})
public class Booking {

    @Id
    @Column(name = "id", nullable = false, length = 64)
    private String id;

    @Column(name = "room_id", nullable = false, length = 64)
    private String roomId;

    @Column(name = "title", length = 255)
    private String title;

    @Column(name = "organiser", nullable = false, length = 128)
    private String organiser;

    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "booking_attendees", joinColumns = @JoinColumn(name = "booking_id"))
    @Column(name = "attendee_email")
    private List<String> attendees = new ArrayList<>();

    @Column(name = "recurrence_group_id", length = 64)
    private String recurrenceGroupId;

    @Column(name = "occurrence_index")
    private Integer occurrenceIndex;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public Booking() {
    }

    public Booking(String id, String roomId, String title, String organiser,
                   LocalDateTime startTime, LocalDateTime endTime,
                   List<String> attendees, String recurrenceGroupId,
                   Integer occurrenceIndex) {
        this.id = id;
        this.roomId = roomId;
        this.title = title != null && !title.isBlank() ? title : "Meeting";
        this.organiser = organiser;
        this.startTime = startTime;
        this.endTime = endTime;
        if (attendees != null) {
            this.attendees = new ArrayList<>(attendees);
        }
        this.recurrenceGroupId = recurrenceGroupId;
        this.occurrenceIndex = occurrenceIndex;
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    @PrePersist
    public void onPrePersist() {
        if (createdAt == null) {
            createdAt = LocalDateTime.now();
        }
        if (updatedAt == null) {
            updatedAt = createdAt;
        }
    }

    @PreUpdate
    public void onPreUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getRoomId() {
        return roomId;
    }

    public void setRoomId(String roomId) {
        this.roomId = roomId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getOrganiser() {
        return organiser;
    }

    public void setOrganiser(String organiser) {
        this.organiser = organiser;
    }

    public LocalDateTime getStartTime() {
        return startTime;
    }

    public void setStartTime(LocalDateTime startTime) {
        this.startTime = startTime;
    }

    public LocalDateTime getEndTime() {
        return endTime;
    }

    public void setEndTime(LocalDateTime endTime) {
        this.endTime = endTime;
    }

    public List<String> getAttendees() {
        return attendees;
    }

    public void setAttendees(List<String> attendees) {
        this.attendees = attendees != null ? new ArrayList<>(attendees) : new ArrayList<>();
    }

    public String getRecurrenceGroupId() {
        return recurrenceGroupId;
    }

    public void setRecurrenceGroupId(String recurrenceGroupId) {
        this.recurrenceGroupId = recurrenceGroupId;
    }

    public Integer getOccurrenceIndex() {
        return occurrenceIndex;
    }

    public void setOccurrenceIndex(Integer occurrenceIndex) {
        this.occurrenceIndex = occurrenceIndex;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Booking booking = (Booking) o;
        return Objects.equals(id, booking.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
