package com.booking.repository;

import com.booking.model.Booking;
import com.booking.model.Room;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class BookingRepository {

    private final Map<String, Booking> bookings = new ConcurrentHashMap<>();
    private final Map<String, Room> rooms = new ConcurrentHashMap<>();

    public Optional<Booking> findById(String id) {
        return Optional.ofNullable(bookings.get(id));
    }

    public List<Booking> findAll() {
        return new ArrayList<>(bookings.values());
    }

    public Booking save(Booking booking) {
        bookings.put(booking.getId(), booking);
        return booking;
    }

    public void deleteById(String id) {
        bookings.remove(id);
    }

    public List<Booking> findByRoomAndDate(String roomId, LocalDate date) {
        return bookings.values().stream()
                .filter(b -> b.getRoomId().equals(roomId) && b.getDate().equals(date))
                .toList();
    }

    public List<Booking> findByDate(LocalDate date) {
        return bookings.values().stream()
                .filter(b -> b.getDate().equals(date))
                .toList();
    }

    // --- Room operations ---

    public void addRoom(Room room) {
        rooms.put(room.id(), room);
    }

    public Optional<Room> findRoomById(String id) {
        return Optional.ofNullable(rooms.get(id));
    }

    public Collection<Room> findAllRooms() {
        return rooms.values();
    }

    public List<Room> findRoomsByMinCapacity(int minCapacity) {
        return rooms.values().stream()
                .filter(r -> r.capacity() >= minCapacity)
                .sorted(Comparator.comparingInt(Room::capacity))
                .toList();
    }
}