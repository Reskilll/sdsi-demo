package com.booking.controller;

import com.booking.dto.*;
import com.booking.model.Booking;
import com.booking.repository.BookingRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@TestMethodOrder(MethodOrderer.MethodName.class)
class BookingControllerTest {

    @Autowired private MockMvc mvc;
    @Autowired private ObjectMapper mapper;
    @Autowired private BookingRepository repo;

    private static String createdId;

    @BeforeEach
    void clear() {
        // fresh state per test — clear all bookings
        repo.findAll().forEach(b -> repo.deleteById(b.getId()));
    }

    // --- M1: CRUD ---

    @Test
    void m1_create() throws Exception {
        String body = """
            {"roomId":"r2","organiser":"alice","date":"2026-11-01",
             "start":"10:00","end":"11:00","attendees":["alice","bob"]}""";

        String resp = mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.roomId").value("r2"))
                .andReturn().getResponse().getContentAsString();

        createdId = mapper.readTree(resp).get("id").asText();
        assertNotNull(createdId);
    }

    @Test
    void m1_readNotFound() throws Exception {
        mvc.perform(get("/api/bookings/nonexistent"))
                .andExpect(status().isNotFound());
    }

    @Test
    void m1_update() throws Exception {
        // create first
        String create = """
            {"roomId":"r3","organiser":"bob","date":"2026-11-02",
             "start":"09:00","end":"10:00","attendees":["bob"]}""";
        String id = mapper.readTree(mvc.perform(post("/api/bookings")
                .contentType(MediaType.APPLICATION_JSON).content(create))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString()).get("id").asText();

        String update = """
            {"roomId":"r4","organiser":"bob","date":"2026-11-02",
             "start":"09:30","end":"10:30","attendees":["bob","carol"]}""";
        mvc.perform(put("/api/bookings/" + id)
                        .contentType(MediaType.APPLICATION_JSON).content(update))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roomId").value("r4"))
                .andExpect(jsonPath("$.attendees.length()").value(2));
    }

    @Test
    void m1_delete() throws Exception {
        String create = """
            {"roomId":"r1","organiser":"dan","date":"2026-11-03",
             "start":"14:00","end":"15:00","attendees":["dan"]}""";
        String id = mapper.readTree(mvc.perform(post("/api/bookings")
                .contentType(MediaType.APPLICATION_JSON).content(create))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString()).get("id").asText();

        mvc.perform(delete("/api/bookings/" + id))
                .andExpect(status().isNoContent());

        mvc.perform(get("/api/bookings/" + id))
                .andExpect(status().isNotFound());
    }

    // --- M2: Overlap rejection ---

    @Test
    void m2_rejectOverlap() throws Exception {
        String first = """
            {"roomId":"r2","organiser":"eve","date":"2026-11-04",
             "start":"10:00","end":"12:00","attendees":["eve"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(first))
                .andExpect(status().isCreated());

        String overlap = """
            {"roomId":"r2","organiser":"frank","date":"2026-11-04",
             "start":"11:00","end":"13:00","attendees":["frank"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(overlap))
                .andExpect(status().isConflict());
    }

    @Test
    void m2_allowBackToBack() throws Exception {
        String first = """
            {"roomId":"r3","organiser":"grace","date":"2026-11-05",
             "start":"10:00","end":"11:00","attendees":["grace"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(first))
                .andExpect(status().isCreated());

        String backToBack = """
            {"roomId":"r3","organiser":"heidi","date":"2026-11-05",
             "start":"11:00","end":"12:00","attendees":["heidi"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(backToBack))
                .andExpect(status().isCreated()); // 200? No, CREATE should be 201
        // but wait, our @ResponseStatus is CREATED which is 201 — correct
    }

    // --- M3: Capacity ---

    @Test
    void m3_rejectCapacityExceeded() throws Exception {
        // Atlas has capacity 4
        String body = """
            {"roomId":"r1","organiser":"ivan","date":"2026-11-06",
             "start":"09:00","end":"10:00",
             "attendees":["a","b","c","d","e"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnprocessableEntity());
    }

    @Test
    void m3_allowWithinCapacity() throws Exception {
        String body = """
            {"roomId":"r1","organiser":"judy","date":"2026-11-06",
             "start":"09:00","end":"10:00",
             "attendees":["a","b","c","d"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated());
    }

    // --- M4: Find slot ---

    @Test
    void m4_findSlotEmptyDay() throws Exception {
        String body = """
            {"durationMinutes":60,"attendeeCount":5,"date":"2026-12-01"}""";
        mvc.perform(post("/api/bookings/find-slot")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.found").value(true))
                .andExpect(jsonPath("$.startTime").value("09:00"));
    }

    @Test
    void m4_findSlotWithExistingBookings() throws Exception {
        // Book a room from 09:00-11:00
        String booking = """
            {"roomId":"r2","organiser":"ken","date":"2026-12-02",
             "start":"09:00","end":"11:00","attendees":["ken"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(booking))
                .andExpect(status().isCreated());

        // Also book r3 from 09:00-10:00
        String booking2 = """
            {"roomId":"r3","organiser":"lena","date":"2026-12-02",
             "start":"09:00","end":"10:00","attendees":["lena"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(booking2))
                .andExpect(status().isCreated());

        // Looking for 5 attendees — r2 (8 cap), r3 (12 cap), r4 (20 cap), r5 (50 cap)
        // r2 occupied 09:00-11:00, so earliest on r2 is 11:00
        // r3 occupied 09:00-10:00, so earliest on r3 is 10:00
        // r4 free at 09:00 — best
        String body = """
            {"durationMinutes":30,"attendeeCount":5,"date":"2026-12-02"}""";
        mvc.perform(post("/api/bookings/find-slot")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.found").value(true))
                .andExpect(jsonPath("$.startTime").value("09:00"))
                .andExpect(jsonPath("$.roomId").value("r4"));
    }

    @Test
    void m4_findSlotNoRoomBigEnough() throws Exception {
        String body = """
            {"durationMinutes":60,"attendeeCount":999,"date":"2026-12-03"}""";
        mvc.perform(post("/api/bookings/find-slot")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.found").value(false));
    }

    // --- M5: Recurring ---

    @Test
    void m5_createRecurring() throws Exception {
        String body = """
            {"roomId":"r3","organiser":"mike","startDate":"2026-11-09",
             "endDate":"2026-11-23","start":"14:00","end":"15:00",
             "attendees":["mike","nina"]}""";
        mvc.perform(post("/api/bookings/recurring")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.successful.length()").value(3)) // 3 Mondays
                .andExpect(jsonPath("$.conflicts.length()").value(0));
    }

    @Test
    void m5_recurringWithConflict() throws Exception {
        // Book a single booking that overlaps one occurrence
        String single = """
            {"roomId":"r4","organiser":"oli","date":"2026-11-16",
             "start":"14:00","end":"15:00","attendees":["oli"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(single))
                .andExpect(status().isCreated());

        // Recurring covers 2026-11-09, 11-16, 11-23 (Mondays)
        String recurring = """
            {"roomId":"r4","organiser":"pam","startDate":"2026-11-09",
             "endDate":"2026-11-23","start":"14:00","end":"15:00",
             "attendees":["pam"]}""";
        mvc.perform(post("/api/bookings/recurring")
                        .contentType(MediaType.APPLICATION_JSON).content(recurring))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.successful.length()").value(2))
                .andExpect(jsonPath("$.conflicts.length()").value(1));
    }

    // --- Validation ---

    @Test
    void validation_missingFields() throws Exception {
        String body = """
            {"roomId":"r1","organiser":"test"}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void validation_invalidTimes() throws Exception {
        String body = """
            {"roomId":"r2","organiser":"test","date":"2026-11-01",
             "start":"15:00","end":"14:00","attendees":["test"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void validation_outsideBusinessHours() throws Exception {
        String body = """
            {"roomId":"r2","organiser":"test","date":"2026-11-01",
             "start":"08:00","end":"09:00","attendees":["test"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest());
    }

    @Test
    void validation_roomNotFound() throws Exception {
        String body = """
            {"roomId":"r99","organiser":"test","date":"2026-11-01",
             "start":"10:00","end":"11:00","attendees":["test"]}""";
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isNotFound());
    }
}