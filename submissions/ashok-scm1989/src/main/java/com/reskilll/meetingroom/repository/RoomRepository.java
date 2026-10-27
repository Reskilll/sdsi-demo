package com.reskilll.meetingroom.repository;

import com.reskilll.meetingroom.model.Room;
import org.springframework.stereotype.Repository;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Repository
public class RoomRepository {

    private final Map<String, Room> roomMap = new ConcurrentHashMap<>();

    public Optional<Room> findById(String id) {
        if (id == null) return Optional.empty();
        return Optional.ofNullable(roomMap.get(id.trim().toUpperCase()));
    }

    public boolean existsById(String id) {
        if (id == null) return false;
        return roomMap.containsKey(id.trim().toUpperCase());
    }

    public List<Room> findAll() {
        return roomMap.values().stream()
                .sorted(Comparator.comparingInt(Room::getCapacity).thenComparing(Room::getId))
                .collect(Collectors.toList());
    }

    public List<Room> findByCapacityGreaterThanEqual(int minCapacity) {
        return roomMap.values().stream()
                .filter(r -> r.getCapacity() >= minCapacity)
                .sorted(Comparator.comparingInt(Room::getCapacity).thenComparing(Room::getId))
                .collect(Collectors.toList());
    }

    public void save(Room room) {
        if (room != null && room.getId() != null) {
            String key = room.getId().trim().toUpperCase();
            room.setId(key);
            roomMap.put(key, room);
        }
    }

    public void saveAll(Collection<Room> rooms) {
        if (rooms != null) {
            rooms.forEach(this::save);
        }
    }

    public void clear() {
        roomMap.clear();
    }

    public long count() {
        return roomMap.size();
    }
}
