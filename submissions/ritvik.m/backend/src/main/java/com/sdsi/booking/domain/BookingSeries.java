package com.sdsi.booking.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Template for a weekly recurring booking. Individual occurrences are
 * {@link Booking} rows linked back through {@code series}.
 */
@Entity
@Table(name = "booking_series")
public class BookingSeries {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "room_id", nullable = false)
    private Room room;

    @Column(name = "organiser", length = 120, nullable = false)
    private String organiser;

    @Column(name = "organiser_email", length = 160)
    private String organiserEmail;

    @Column(name = "title", length = 160, nullable = false)
    private String title;

    @Column(name = "description", length = 1000)
    private String description;

    @Column(name = "start_time", nullable = false)
    private LocalTime startTime;

    @Column(name = "end_time", nullable = false)
    private LocalTime endTime;

    @Column(name = "starts_on", nullable = false)
    private LocalDate startsOn;

    @Column(name = "weeks", nullable = false)
    private int weeks;

    @Column(name = "days_of_week", length = 100, nullable = false)
    private String daysOfWeek;

    @Column(name = "attendee_count", nullable = false)
    private int attendeeCount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(name = "series_attendee", joinColumns = @JoinColumn(name = "series_id"))
    @Column(name = "email", length = 160, nullable = false)
    private Set<String> attendees = new LinkedHashSet<>();

    protected BookingSeries() {
        // for JPA
    }

    public BookingSeries(UUID id, Room room, String organiser, String organiserEmail, String title,
                         String description, LocalTime startTime, LocalTime endTime, LocalDate startsOn,
                         int weeks, Set<DayOfWeek> daysOfWeek, int attendeeCount, Set<String> attendees) {
        this.id = id;
        this.room = room;
        this.organiser = organiser;
        this.organiserEmail = organiserEmail;
        this.title = title;
        this.description = description;
        this.startTime = startTime;
        this.endTime = endTime;
        this.startsOn = startsOn;
        this.weeks = weeks;
        setDaysOfWeek(daysOfWeek);
        this.attendeeCount = attendeeCount;
        this.attendees = attendees == null ? new LinkedHashSet<>() : new LinkedHashSet<>(attendees);
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public Room getRoom() {
        return room;
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

    public LocalTime getStartTime() {
        return startTime;
    }

    public LocalTime getEndTime() {
        return endTime;
    }

    public LocalDate getStartsOn() {
        return startsOn;
    }

    public int getWeeks() {
        return weeks;
    }

    public String getDaysOfWeek() {
        return daysOfWeek;
    }

    public int getAttendeeCount() {
        return attendeeCount;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Set<String> getAttendees() {
        return Collections.unmodifiableSet(attendees);
    }

    public Set<DayOfWeek> dayOfWeekSet() {
        if (daysOfWeek == null || daysOfWeek.isBlank()) {
            return Collections.emptySet();
        }
        return Arrays.stream(daysOfWeek.split(","))
                .map(String::trim)
                .filter(value -> !value.isEmpty())
                .map(DayOfWeek::valueOf)
                .collect(Collectors.toCollection(() -> new TreeSet<>()));
    }

    private void setDaysOfWeek(Collection<DayOfWeek> days) {
        if (days == null || days.isEmpty()) {
            throw new IllegalArgumentException("daysOfWeek must not be empty");
        }
        this.daysOfWeek = new TreeSet<>(days).stream()
                .map(Enum::name)
                .collect(Collectors.joining(","));
    }
}
