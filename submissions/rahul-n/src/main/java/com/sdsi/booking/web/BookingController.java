package com.sdsi.booking.web;

import com.sdsi.booking.service.BookingService;
import com.sdsi.booking.service.FindSlotService;
import com.sdsi.booking.service.RecurrenceService;
import com.sdsi.booking.web.dto.BookingDtos;
import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api")
public class BookingController {

    private final BookingService bookingService;
    private final FindSlotService findSlotService;
    private final RecurrenceService recurrenceService;

    public BookingController(BookingService bookingService,
                             FindSlotService findSlotService,
                             RecurrenceService recurrenceService) {
        this.bookingService = bookingService;
        this.findSlotService = findSlotService;
        this.recurrenceService = recurrenceService;
    }

    // ------------------------------------------------------------------ M1 CRUD

    @PostMapping("/bookings")
    public ResponseEntity<BookingDtos.BookingResponse> create(
            @Valid @RequestBody BookingDtos.BookingRequest request, UriComponentsBuilder uri) {
        BookingDtos.BookingResponse created = bookingService.create(request);
        URI location = uri.path("/api/bookings/{id}").buildAndExpand(created.id()).toUri();
        return ResponseEntity.created(location).body(created);
    }

    @GetMapping("/bookings")
    public List<BookingDtos.BookingResponse> list(
            @RequestParam(required = false) Long roomId) {
        return bookingService.list(roomId);
    }

    @GetMapping("/bookings/{id}")
    public BookingDtos.BookingResponse get(@PathVariable Long id) {
        return bookingService.get(id);
    }

    @PutMapping("/bookings/{id}")
    public BookingDtos.BookingResponse reschedule(@PathVariable Long id,
                                                  @Valid @RequestBody BookingDtos.BookingRequest request) {
        return bookingService.reschedule(id, request);
    }

    @DeleteMapping("/bookings/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        bookingService.delete(id);
    }

    @GetMapping("/rooms")
    public List<BookingDtos.RoomResponse> rooms() {
        return bookingService.listRooms();
    }

    // --------------------------------------------------------------- M4 find-slot

    @GetMapping("/bookings/find-slot")
    public BookingDtos.SlotSuggestion findSlot(
            @RequestParam int duration,
            @RequestParam int attendeeCount,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return findSlotService.findSlot(duration, attendeeCount, date);
    }

    // ------------------------------------------------------ M5 recurrence dry-run

    /** Step 1 — validate the weekly series and report per-date availability. Persists nothing. */
    @PostMapping("/bookings/recurring/dry-run")
    public BookingDtos.RecurrenceDryRunResponse dryRun(
            @Valid @RequestBody BookingDtos.BookingRequest request,
            @RequestParam(defaultValue = "4") int occurrences) {
        return recurrenceService.dryRun(request, occurrences);
    }

    /** Step 2 — commit the vetted plan; saves only the slots that survive re-validation. */
    @PostMapping("/bookings/recurring/confirm")
    public BookingDtos.RecurrenceCommitResponse confirm(
            @Valid @RequestBody BookingDtos.RecurrenceCommitRequest request) {
        return recurrenceService.commit(request.planToken(), request.occurrences());
    }
}
