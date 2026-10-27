package com.sdsi.booking.web;

import com.sdsi.booking.service.SlotService;
import com.sdsi.booking.web.dto.SlotSearchResponse;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping({"/api/find-slot", "/api/slots"})
public class SlotController {

    private final SlotService slotService;

    public SlotController(SlotService slotService) {
        this.slotService = slotService;
    }

    @GetMapping
    public SlotSearchResponse find(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
            @RequestParam int durationMinutes,
            @RequestParam int attendees,
            @RequestParam(required = false) List<String> amenities,
            @RequestParam(required = false) String roomId) {
        return slotService.findSlot(date, durationMinutes, attendees, amenities, roomId);
    }
}
