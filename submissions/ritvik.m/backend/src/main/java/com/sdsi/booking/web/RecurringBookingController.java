package com.sdsi.booking.web;

import com.sdsi.booking.service.RecurringBookingService;
import com.sdsi.booking.web.dto.RecurringBookingRequest;
import com.sdsi.booking.web.dto.RecurringCreateResponse;
import com.sdsi.booking.web.dto.RecurringPreviewResponse;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
@RequestMapping("/api/bookings/recurring")
public class RecurringBookingController {

    private final RecurringBookingService recurringBookingService;

    public RecurringBookingController(RecurringBookingService recurringBookingService) {
        this.recurringBookingService = recurringBookingService;
    }

    /**
     * Dry run: reports per-occurrence conflicts without writing anything.
     */
    @PostMapping("/preview")
    public RecurringPreviewResponse preview(@Valid @RequestBody RecurringBookingRequest request) {
        return recurringBookingService.preview(request);
    }

    @PostMapping
    public ResponseEntity<RecurringCreateResponse> create(
            @Valid @RequestBody RecurringBookingRequest request) {
        RecurringCreateResponse response = recurringBookingService.create(request);
        return ResponseEntity
                .created(URI.create("/api/series/" + response.seriesId()))
                .body(response);
    }
}
