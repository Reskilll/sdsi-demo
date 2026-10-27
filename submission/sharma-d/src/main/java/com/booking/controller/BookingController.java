package com.booking.controller;

import com.booking.dto.*;
import com.booking.model.Booking;
import com.booking.service.BookingService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/bookings")
public class BookingController {

    private final BookingService service;

    public BookingController(BookingService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Booking create(@Valid @RequestBody BookingRequest req) {
        return service.createBooking(req);
    }

    @GetMapping("/{id}")
    public Booking get(@PathVariable String id) {
        return service.getBooking(id);
    }

    @GetMapping
    public List<Booking> getAll() {
        return service.getAllBookings();
    }

    @PutMapping("/{id}")
    public Booking update(@PathVariable String id, @Valid @RequestBody BookingRequest req) {
        return service.updateBooking(id, req);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable String id) {
        service.deleteBooking(id);
    }

    @PostMapping("/find-slot")
    public FindSlotResponse findSlot(@Valid @RequestBody FindSlotRequest req) {
        return service.findSlot(req);
    }

    @PostMapping("/recurring")
    @ResponseStatus(HttpStatus.CREATED)
    public RecurringBookingResponse createRecurring(@Valid @RequestBody RecurringBookingRequest req) {
        return service.createRecurring(req);
    }
}