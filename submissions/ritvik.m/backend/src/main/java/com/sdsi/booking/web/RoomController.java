package com.sdsi.booking.web;

import com.sdsi.booking.service.RoomService;
import com.sdsi.booking.service.SlotService;
import com.sdsi.booking.web.dto.RoomAvailabilityResponse;
import com.sdsi.booking.web.dto.RoomResponse;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/rooms")
public class RoomController {

    private final RoomService roomService;
    private final SlotService slotService;

    public RoomController(RoomService roomService, SlotService slotService) {
        this.roomService = roomService;
        this.slotService = slotService;
    }

    @GetMapping
    public List<RoomResponse> list() {
        return roomService.list();
    }

    @GetMapping("/{id}")
    public RoomResponse get(@PathVariable String id) {
        return roomService.get(id);
    }

    @GetMapping("/{id}/availability")
    public RoomAvailabilityResponse availability(
            @PathVariable String id,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return slotService.availability(id, date);
    }
}
