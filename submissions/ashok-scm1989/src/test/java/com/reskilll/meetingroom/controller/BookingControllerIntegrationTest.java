package com.reskilll.meetingroom.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.reskilll.meetingroom.dto.CreateBookingRequest;
import com.reskilll.meetingroom.dto.RecurringBookingRequest;
import com.reskilll.meetingroom.model.RecurrencePolicy;
import com.reskilll.meetingroom.repository.BookingRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookingControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private BookingRepository bookingRepository;

    private final LocalDate testDate = LocalDate.of(2026, 11, 3);

    @BeforeEach
    void setUp() {
        bookingRepository.deleteAll();
    }

    @Test
    @DisplayName("POST /api/bookings returns 201 Created on valid booking (M1)")
    void testCreateBooking_success() throws Exception {
        CreateBookingRequest req = new CreateBookingRequest(
                "ROOM-101",
                "Product Design Sync",
                "sarah@example.com",
                testDate.atTime(10, 0),
                testDate.atTime(11, 0),
                List.of("designer@example.com", "sarah@example.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.roomId").value("ROOM-101"))
                .andExpect(jsonPath("$.organiser").value("sarah@example.com"))
                .andExpect(jsonPath("$.attendeeCount").value(2));
    }

    @Test
    @DisplayName("POST /api/bookings returns 409 Conflict on overlap (M2)")
    void testCreateBooking_overlapConflict() throws Exception {
        CreateBookingRequest initial = new CreateBookingRequest(
                "ROOM-101",
                "Morning Standup",
                "alice@example.com",
                testDate.atTime(10, 0),
                testDate.atTime(11, 0),
                List.of("alice@example.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(initial)))
                .andExpect(status().isCreated());

        CreateBookingRequest conflicting = new CreateBookingRequest(
                "ROOM-101",
                "Conflicting Meeting",
                "bob@example.com",
                testDate.atTime(10, 30),
                testDate.atTime(11, 30),
                List.of("bob@example.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(conflicting)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BOOKING_CONFLICT"))
                .andExpect(jsonPath("$.message", containsString("already booked")));
    }

    @Test
    @DisplayName("POST /api/bookings allows back-to-back booking (M2)")
    void testCreateBooking_backToBackAllowed() throws Exception {
        CreateBookingRequest first = new CreateBookingRequest(
                "ROOM-101",
                "First Meeting",
                "alice@example.com",
                testDate.atTime(10, 0),
                testDate.atTime(11, 0),
                List.of("alice@example.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(first)))
                .andExpect(status().isCreated());

        // Exactly back-to-back: starts at 11:00
        CreateBookingRequest backToBack = new CreateBookingRequest(
                "ROOM-101",
                "Back To Back Meeting",
                "bob@example.com",
                testDate.atTime(11, 0),
                testDate.atTime(12, 0),
                List.of("bob@example.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(backToBack)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists());
    }

    @Test
    @DisplayName("POST /api/bookings returns 400 Bad Request on capacity exceeded (M3)")
    void testCreateBooking_capacityExceeded() throws Exception {
        // ROOM-PHONE-1 max capacity is 2
        CreateBookingRequest req = new CreateBookingRequest(
                "ROOM-PHONE-1",
                "Crowded Booth",
                "alice@example.com",
                testDate.atTime(14, 0),
                testDate.atTime(15, 0),
                List.of("u1@ex.com", "u2@ex.com", "u3@ex.com")
        );

        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("CAPACITY_EXCEEDED"))
                .andExpect(jsonPath("$.details.roomCapacity").value(2))
                .andExpect(jsonPath("$.details.requestedAttendees").value(3));
    }

    @Test
    @DisplayName("GET /api/rooms/find-slot returns earliest free slot (M4)")
    void testFindSlot_endpoint() throws Exception {
        mockMvc.perform(get("/api/rooms/find-slot")
                        .param("date", testDate.toString())
                        .param("duration", "45")
                        .param("attendees", "4"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roomId").isNotEmpty())
                .andExpect(jsonPath("$.startTime").value(testDate + "T09:00:00"))
                .andExpect(jsonPath("$.endTime").value(testDate + "T09:45:00"))
                .andExpect(jsonPath("$.durationMinutes").value(45));
    }

    @Test
    @DisplayName("POST /api/bookings/recurring returns per-occurrence conflict details (M5)")
    void testRecurringBooking_endpoint() throws Exception {
        // Pre-book week 2
        CreateBookingRequest blocker = new CreateBookingRequest(
                "ROOM-102",
                "Existing Meeting",
                "blocker@example.com",
                testDate.plusWeeks(1).atTime(10, 0),
                testDate.plusWeeks(1).atTime(11, 0),
                List.of("blocker@example.com")
        );
        mockMvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(blocker)))
                .andExpect(status().isCreated());

        RecurringBookingRequest recReq = new RecurringBookingRequest(
                "ROOM-102",
                "Weekly Standup",
                "lead@example.com",
                testDate.atTime(10, 0),
                testDate.atTime(11, 0),
                List.of("lead@example.com"),
                3,
                RecurrencePolicy.BOOK_AVAILABLE
        );

        mockMvc.perform(post("/api/bookings/recurring")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(recReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.totalRequested").value(3))
                .andExpect(jsonPath("$.successfulCount").value(2))
                .andExpect(jsonPath("$.conflictCount").value(1))
                .andExpect(jsonPath("$.conflicts[0].occurrenceIndex").value(2))
                .andExpect(jsonPath("$.conflicts[0].conflictingOrganiser").value("blocker@example.com"));
    }

    @Test
    @DisplayName("GET /api/rooms returns seeded room catalog (M3)")
    void testGetRooms() throws Exception {
        mockMvc.perform(get("/api/rooms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(5))))
                .andExpect(jsonPath("$[0].id").exists())
                .andExpect(jsonPath("$[0].capacity").isNumber());
    }
}
