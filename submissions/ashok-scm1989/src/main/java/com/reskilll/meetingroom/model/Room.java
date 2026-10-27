package com.reskilll.meetingroom.model;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class Room {
    private String id;
    private String name;
    private int capacity;
    private int floor;
    private List<String> amenities = new ArrayList<>();

    public Room() {
    }

    public Room(String id, String name, int capacity, int floor, List<String> amenities) {
        this.id = id;
        this.name = name;
        this.capacity = capacity;
        this.floor = floor;
        if (amenities != null) {
            this.amenities = new ArrayList<>(amenities);
        }
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getCapacity() {
        return capacity;
    }

    public void setCapacity(int capacity) {
        this.capacity = capacity;
    }

    public int getFloor() {
        return floor;
    }

    public void setFloor(int floor) {
        this.floor = floor;
    }

    public List<String> getAmenities() {
        return amenities;
    }

    public void setAmenities(List<String> amenities) {
        this.amenities = amenities != null ? new ArrayList<>(amenities) : new ArrayList<>();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Room room = (Room) o;
        return Objects.equals(id, room.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "Room{" +
                "id='" + id + '\'' +
                ", name='" + name + '\'' +
                ", capacity=" + capacity +
                ", floor=" + floor +
                '}';
    }
}
