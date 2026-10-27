package com.sdsi.booking.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Table;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

@Entity
@Table(name = "room")
public class Room {

    @Id
    @Column(name = "id", length = 40, nullable = false)
    private String id;

    @Column(name = "name", length = 80, nullable = false, unique = true)
    private String name;

    @Column(name = "capacity", nullable = false)
    private int capacity;

    @Column(name = "floor")
    private Integer floor;

    @Column(name = "location", length = 120)
    private String location;

    @Column(name = "active", nullable = false)
    private boolean active = true;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(name = "room_amenity", joinColumns = @JoinColumn(name = "room_id"))
    @Column(name = "amenity", length = 40, nullable = false)
    private Set<String> amenities = new LinkedHashSet<>();

    protected Room() {
        // for JPA
    }

    public Room(String id, String name, int capacity, Integer floor, String location, Set<String> amenities) {
        this.id = Objects.requireNonNull(id, "id");
        this.name = Objects.requireNonNull(name, "name");
        if (capacity < 1) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        this.capacity = capacity;
        this.floor = floor;
        this.location = location;
        this.amenities = amenities == null ? new LinkedHashSet<>() : new LinkedHashSet<>(amenities);
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public int getCapacity() {
        return capacity;
    }

    public Integer getFloor() {
        return floor;
    }

    public String getLocation() {
        return location;
    }

    public boolean isActive() {
        return active;
    }

    public void setActive(boolean active) {
        this.active = active;
    }

    public Set<String> getAmenities() {
        return Collections.unmodifiableSet(amenities);
    }
}
