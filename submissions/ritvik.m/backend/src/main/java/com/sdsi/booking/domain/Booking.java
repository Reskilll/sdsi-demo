package com.sdsi.booking.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "booking")
public class Booking {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "room_id", nullable = false)
    private Room room;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "series_id")
    private BookingSeries series;

    @Column(name = "occurrence_index")
    private Integer occurrenceIndex;

    @Column(name = "organiser", length = 120, nullable = false)
    private String organiser;

    @Column(name = "organiser_email", length = 160)
    private String organiserEmail;

    @Column(name = "title", length = 160, nullable = false)
    private String title;

    @Column(name = "description", length = 1000)
    private String description;

    @Column(name = "start_at", nullable = false)
    private LocalDateTime start;

    @Column(name = "end_at", nullable = false)
    private LocalDateTime end;

    @Column(name = "attendee_count", nullable = false)
    private int attendeeCount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 16, nullable = false)
    private BookingStatus status = BookingStatus.CONFIRMED;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(name = "booking_attendee", joinColumns = @JoinColumn(name = "booking_id"))
    @Column(name = "email", length = 160, nullable = false)
    private Set<String> attendees = new LinkedHashSet<>();

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Version
    @Column(name = "version", nullable = false)
    private long version;

    protected Booking() {
        // for JPA
    }

    public Booking(UUID id, Room room, BookingSeries series, Integer occurrenceIndex, String organiser,
                   String organiserEmail, String title, String description, LocalDateTime start,
                   LocalDateTime end, int attendeeCount, Set<String> attendees) {
        this.id = id;
        this.room = room;
        this.series = series;
        this.occurrenceIndex = occurrenceIndex;
        this.organiser = organiser;
        this.organiserEmail = organiserEmail;
        this.title = title;
        this.description = description;
        this.start = start;
        this.end = end;
        this.attendeeCount = attendeeCount;
        this.attendees = attendees == null ? new LinkedHashSet<>() : new LinkedHashSet<>(attendees);
        this.status = BookingStatus.CONFIRMED;
        Instant now = Instant.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    @PrePersist
    void onCreate() {
        Instant now = Instant.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    @PreUpdate
    void onUpdate() {
        this.updatedAt = Instant.now();
    }

    public void apply(String organiser, String organiserEmail, String title, String description,
                      Room room, LocalDateTime start, LocalDateTime end, int attendeeCount, Set<String> attendees) {
        this.organiser = organiser;
        this.organiserEmail = organiserEmail;
        this.title = title;
        this.description = description;
        this.room = room;
        this.start = start;
        this.end = end;
        this.attendeeCount = attendeeCount;
        this.attendees = attendees == null ? new LinkedHashSet<>() : new LinkedHashSet<>(attendees);
    }

    public void cancel() {
        this.status = BookingStatus.CANCELLED;
    }

    public UUID getId() {
        return id;
    }

    public Room getRoom() {
        return room;
    }

    public BookingSeries getSeries() {
        return series;
    }

    public Integer getOccurrenceIndex() {
        return occurrenceIndex;
    }

    public String getOrganiser() {
        return organiser;
    }

    public String getOrganiserEmail() {
        return organiserEmail;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public LocalDateTime getStart() {
        return start;
    }

    public LocalDateTime getEnd() {
        return end;
    }

    public int getAttendeeCount() {
        return attendeeCount;
    }

    public BookingStatus getStatus() {
        return status;
    }

    public Set<String> getAttendees() {
        return Collections.unmodifiableSet(attendees);
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public long getVersion() {
        return version;
    }
}
