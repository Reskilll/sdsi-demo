package com.sdsi.booking.web;

import com.sdsi.booking.domain.BookingStatus;
import com.sdsi.booking.service.BookingQuery;
import com.sdsi.booking.service.BookingService;
import com.sdsi.booking.web.dto.BookingCreateRequest;
import com.sdsi.booking.web.dto.BookingResponse;
import com.sdsi.booking.web.dto.BookingUpdateRequest;
import com.sdsi.booking.web.dto.PageResponse;
import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@RestController
@RequestMapping("/api/bookings")
public class BookingController {

    private final BookingService bookingService;

    public BookingController(BookingService bookingService) {
        this.bookingService = bookingService;
    }

    @PostMapping
    public ResponseEntity<BookingResponse> create(@Valid @RequestBody BookingCreateRequest request) {
        BookingResponse created = bookingService.create(request);
        return ResponseEntity
                .created(URI.create("/api/bookings/" + created.id()))
                .body(created);
    }

    @GetMapping("/{id}")
    public BookingResponse get(@PathVariable UUID id) {
        return bookingService.get(id);
    }

    @PutMapping("/{id}")
    public BookingResponse update(@PathVariable UUID id,
                                  @Valid @RequestBody BookingUpdateRequest request) {
        return bookingService.update(id, request);
    }

    @PatchMapping("/{id}/cancel")
    public BookingResponse cancel(@PathVariable UUID id) {
        return bookingService.cancel(id);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {
        bookingService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping
    public PageResponse<BookingResponse> list(
            @RequestParam(required = false) String roomId,
            @RequestParam(required = false) String organiser,
            @RequestParam(required = false) BookingStatus status,
            @RequestParam(required = false) UUID seriesId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return bookingService.search(new BookingQuery(roomId, organiser, status, seriesId,
                date, from, to, page, size));
    }

    @GetMapping(value = "/{id}/ics", produces = "text/calendar")
    public ResponseEntity<String> ics(@PathVariable UUID id) {
        String calendar = bookingService.ics(id);
        String filename = "booking-" + id + ".ics";
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "calendar", StandardCharsets.UTF_8))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename(filename).build().toString())
                .body(calendar);
    }
}
