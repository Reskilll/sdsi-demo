package com.reskilll.meetingroom.service;

import com.reskilll.meetingroom.exception.CapacityExceededException;
import com.reskilll.meetingroom.exception.ResourceNotFoundException;
import com.reskilll.meetingroom.model.Room;
import com.reskilll.meetingroom.repository.RoomRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RoomService {

    private final RoomRepository roomRepository;

    public RoomService(RoomRepository roomRepository) {
        this.roomRepository = roomRepository;
    }

    public List<Room> getAllRooms() {
        return roomRepository.findAll();
    }

    public Room getRoomById(String roomId) {
        if (roomId == null || roomId.isBlank()) {
            throw new ResourceNotFoundException("Room ID cannot be empty");
        }
        return roomRepository.findById(roomId.trim())
                .orElseThrow(() -> new ResourceNotFoundException("Room not found with ID: " + roomId));
    }

    public boolean roomExists(String roomId) {
        return roomId != null && roomRepository.existsById(roomId.trim());
    }

    /**
     * Validates that requested attendees do not exceed the room's maximum capacity (M3).
     */
    public void validateCapacity(String roomId, int attendeeCount) {
        Room room = getRoomById(roomId);
        if (attendeeCount > room.getCapacity()) {
            throw new CapacityExceededException(room.getId(), attendeeCount, room.getCapacity());
        }
    }

    public List<Room> getEligibleRooms(int attendeeCount) {
        return roomRepository.findByCapacityGreaterThanEqual(attendeeCount);
    }
}
