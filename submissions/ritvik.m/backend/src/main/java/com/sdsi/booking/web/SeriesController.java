package com.sdsi.booking.web;

import com.sdsi.booking.service.RecurringBookingService;
import com.sdsi.booking.web.dto.CancelSeriesResponse;
import com.sdsi.booking.web.dto.PageResponse;
import com.sdsi.booking.web.dto.SeriesResponse;
import com.sdsi.booking.web.dto.SeriesSummaryResponse;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.UUID;

@RestController
@RequestMapping("/api/series")
public class SeriesController {

    private final RecurringBookingService service;

    public SeriesController(RecurringBookingService service) {
        this.service = service;
    }

    @GetMapping
    public PageResponse<SeriesSummaryResponse> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return service.listSeries(page, size);
    }

    @GetMapping("/{id}")
    public SeriesResponse get(@PathVariable UUID id) {
        return service.getSeries(id);
    }

    /**
     * Cancels confirmed occurrences starting at or after {@code from}
     * (defaults to now). Earlier occurrences are preserved for audit purposes.
     */
    @DeleteMapping("/{id}")
    public CancelSeriesResponse cancel(
            @PathVariable UUID id,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            LocalDateTime from) {
        return service.cancelSeries(id, from);
    }
}
