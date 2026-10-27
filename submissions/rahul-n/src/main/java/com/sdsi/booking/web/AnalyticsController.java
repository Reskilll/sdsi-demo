package com.sdsi.booking.web;

import com.sdsi.booking.service.UtilizationService;
import com.sdsi.booking.web.dto.BookingDtos;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

/** Stretch: per-room operational utilization over a week. */
@RestController
@RequestMapping("/api/analytics")
public class AnalyticsController {

    private final UtilizationService utilizationService;

    public AnalyticsController(UtilizationService utilizationService) {
        this.utilizationService = utilizationService;
    }

    @GetMapping("/utilization")
    public BookingDtos.UtilizationResponse utilization(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate weekStart) {
        return utilizationService.utilization(weekStart);
    }
}
