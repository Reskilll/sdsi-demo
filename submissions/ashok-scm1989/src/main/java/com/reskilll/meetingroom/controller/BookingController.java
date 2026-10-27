package com.reskilll.meetingroom.controller;

import com.reskilll.meetingroom.dto.BookingResponse;
import com.reskilll.meetingroom.dto.CreateBookingRequest;
import com.reskilll.meetingroom.dto.RecurringBookingRequest;
import com.reskilll.meetingroom.dto.RecurringBookingResult;
import com.reskilll.meetingroom.dto.UpdateBookingRequest;
import com.reskilll.meetingroom.service.BookingService;
import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/bookings")
@CrossOrigin(origins = "*")
public class BookingController {

    private final BookingService bookingService;

    public BookingController(BookingService bookingService) {
        this.bookingService = bookingService;
    }

    /**
     * M1 & M2 & M3: Create a new booking.
     */
    @PostMapping
    public ResponseEntity<BookingResponse> createBooking(@Valid @RequestBody CreateBookingRequest request) {
        BookingResponse created = bookingService.createBooking(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    /**
     * M1: Get booking by ID.
     */
    @GetMapping("/{id}")
    public ResponseEntity<BookingResponse> getBooking(@PathVariable String id) {
        BookingResponse booking = bookingService.getBooking(id);
        return ResponseEntity.ok(booking);
    }

    /**
     * M1: List bookings with optional filtering.
     */
    @GetMapping
    public ResponseEntity<List<BookingResponse>> listBookings(
            @RequestParam(required = false) String roomId,
            @RequestParam(required = false) String organiser,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        List<BookingResponse> list = bookingService.listBookings(roomId, organiser, date);
        return ResponseEntity.ok(list);
    }

    /**
     * M1 & M2 & M3: Update existing booking.
     */
    @PutMapping("/{id}")
    public ResponseEntity<BookingResponse> updateBooking(
            @PathVariable String id,
            @RequestBody UpdateBookingRequest request) {
        BookingResponse updated = bookingService.updateBooking(id, request);
        return ResponseEntity.ok(updated);
    }

    /**
     * M1: Delete booking by ID.
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteBooking(@PathVariable String id) {
        bookingService.deleteBooking(id);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Booking " + id + " deleted successfully",
                "deletedBookingId", id
        ));
    }

    /**
     * M5: Create weekly recurring bookings with per-occurrence conflict reporting.
     */
    @PostMapping("/recurring")
    public ResponseEntity<RecurringBookingResult> createRecurringBooking(
            @Valid @RequestBody RecurringBookingRequest request) {
        RecurringBookingResult result = bookingService.createRecurringBooking(request);
        HttpStatus status = result.getConflictCount() > 0 && result.getSuccessfulCount() == 0
                ? HttpStatus.CONFLICT
                : HttpStatus.CREATED;
        return ResponseEntity.status(status).body(result);
    }

    /**
     * Delete entire recurring group.
     */
    @DeleteMapping("/recurring/{recurrenceGroupId}")
    public ResponseEntity<Map<String, Object>> deleteRecurringGroup(@PathVariable String recurrenceGroupId) {
        long deletedCount = bookingService.deleteRecurringGroup(recurrenceGroupId);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "recurrenceGroupId", recurrenceGroupId,
                "deletedOccurrences", deletedCount
        ));
    }
}
