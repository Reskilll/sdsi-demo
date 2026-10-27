package com.reskilll.meetingroom.controller;

import com.reskilll.meetingroom.dto.SlotRecommendation;
import com.reskilll.meetingroom.model.Room;
import com.reskilll.meetingroom.service.BookingService;
import com.reskilll.meetingroom.service.RoomService;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/rooms")
@CrossOrigin(origins = "*")
public class RoomController {

    private final RoomService roomService;
    private final BookingService bookingService;

    public RoomController(RoomService roomService, BookingService bookingService) {
        this.roomService = roomService;
        this.bookingService = bookingService;
    }

    /**
     * List all meeting rooms (loaded from rooms.json).
     */
    @GetMapping
    public ResponseEntity<List<Room>> getAllRooms() {
        return ResponseEntity.ok(roomService.getAllRooms());
    }

    /**
     * Get room details by room ID.
     */
    @GetMapping("/{id}")
    public ResponseEntity<Room> getRoomById(@PathVariable String id) {
        return ResponseEntity.ok(roomService.getRoomById(id));
    }

    /**
     * M4: Find-slot.
     * Given duration (in minutes), attendee count, and date:
     * returns earliest free room and time between 09:00 and 18:00.
     *
     * Example:
     * GET /api/rooms/find-slot?date=2026-10-28&duration=45&attendees=6
     */
    @GetMapping("/find-slot")
    public ResponseEntity<SlotRecommendation> findSlot(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
            @RequestParam(required = false) Integer duration,
            @RequestParam(required = false) Integer durationMinutes,
            @RequestParam(required = false) Integer attendees,
            @RequestParam(required = false) Integer attendeeCount) {

        int dur = duration != null ? duration : (durationMinutes != null ? durationMinutes : 30);
        int att = attendees != null ? attendees : (attendeeCount != null ? attendeeCount : 1);

        SlotRecommendation slot = bookingService.findEarliestSlot(date, dur, att);
        return ResponseEntity.ok(slot);
    }
}
