package com.sdsi.booking;

import com.fasterxml.jackson.databind.JsonNode;
import com.sdsi.booking.support.IntegrationTestBase;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class BookingApiTest extends IntegrationTestBase {

    @Test
    void fullCrudLifecycle() throws Exception {
        LocalDate date = futureDate();
        LocalDateTime start = date.atTime(10, 0);
        LocalDateTime end = date.atTime(11, 0);

        MvcResult created = postBooking(bookingPayload("atlas", start, end, 4))
                .andExpect(status().isCreated())
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.room.id").value("atlas"))
                .andExpect(jsonPath("$.status").value("CONFIRMED"))
                .andExpect(jsonPath("$.version").value(0))
                .andExpect(jsonPath("$.createdAt").exists())
                .andExpect(jsonPath("$.updatedAt").exists())
                .andExpect(jsonPath("$.organiserEmail").value("ritvik@example.com"))
                .andReturn();
        String id = json(created).get("id").asText();

        mockMvc.perform(get("/api/bookings/{id}", id).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Planning"))
                .andExpect(jsonPath("$.attendeeCount").value(4))
                .andExpect(jsonPath("$.room.capacity").value(4));

        mockMvc.perform(get("/api/bookings").param("date", date.toString())
                        .param("roomId", "atlas").param("organiser", "RITVIK").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1));

        Map<String, Object> update = bookingPayload("atlas", date.atTime(11, 0), date.atTime(12, 0), 4);
        update.put("title", "Updated planning");
        update.put("version", 0);
        mockMvc.perform(jsonRequest(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", id), update))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Updated planning"))
                .andExpect(jsonPath("$.version").value(1))
                .andExpect(jsonPath("$.start").value(date + "T11:00:00"));

        Map<String, Object> stale = new LinkedHashMap<>(update);
        stale.put("title", "Stale edit");
        mockMvc.perform(jsonRequest(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", id), stale))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("STALE_VERSION"));

        mockMvc.perform(patch("/api/bookings/{id}/cancel", id).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"));

        mockMvc.perform(patch("/api/bookings/{id}/cancel", id).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"));

        Map<String, Object> afterCancel = bookingPayload("atlas", date.atTime(11, 0), date.atTime(12, 0), 4);
        mockMvc.perform(jsonRequest(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", id), afterCancel))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("BOOKING_CANCELLED"));

        mockMvc.perform(delete("/api/bookings/{id}", id).with(auth()))
                .andExpect(status().isNoContent());
        mockMvc.perform(get("/api/bookings/{id}", id).with(auth()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void attendeesCanBeDerivedFromListAndAreDeduplicated() throws Exception {
        LocalDate date = futureDate();
        Map<String, Object> body = bookingPayload("atlas", date.atTime(9, 0), date.atTime(10, 0), 2);
        body.remove("attendeeCount");
        body.put("attendees", List.of("Ada", "Grace", "Ada"));

        MvcResult result = postBooking(body)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.attendeeCount").value(2))
                .andExpect(jsonPath("$.attendees.length()").value(2))
                .andReturn();
        assertThat(json(result).get("attendees").toString()).contains("Ada", "Grace");
    }

    @Test
    void mismatchedAttendeesAreRejected() throws Exception {
        LocalDate date = futureDate();
        Map<String, Object> body = bookingPayload("atlas", date.atTime(9, 0), date.atTime(10, 0), 4);
        body.put("attendees", List.of("Ada", "Grace"));

        postBooking(body)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("ATTENDEE_COUNT_MISMATCH"));
    }

    @Test
    void cancelledBookingFreesItsSlot() throws Exception {
        LocalDate date = futureDate();
        LocalDateTime start = date.atTime(13, 0);
        LocalDateTime end = date.atTime(14, 0);
        JsonNode first = createBooking("atlas", start, end, 2);

        mockMvc.perform(patch("/api/bookings/{id}/cancel", first.get("id").asText()).with(auth()))
                .andExpect(status().isOk());

        createBooking("atlas", start, end, 3);
    }

    @Test
    void paginationAndFiltersWork() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 1);
        createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 1);
        createBooking("orion", date.atTime(9, 0), date.atTime(10, 0), 5);

        mockMvc.perform(get("/api/bookings").param("date", date.toString())
                        .param("page", "0").param("size", "2").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(3))
                .andExpect(jsonPath("$.totalPages").value(2))
                .andExpect(jsonPath("$.content.length()").value(2))
                .andExpect(jsonPath("$.first").value(true))
                .andExpect(jsonPath("$.last").value(false));

        mockMvc.perform(get("/api/bookings").param("roomId", "orion").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1))
                .andExpect(jsonPath("$.content[0].room.id").value("orion"));
    }

    @Test
    void icsExportIsAValidCalendarAndEscapesUserText() throws Exception {
        LocalDate date = futureDate();
        Map<String, Object> body = bookingPayload("atlas", date.atTime(15, 0), date.atTime(16, 0), 2);
        body.put("title", "Sync, planning; Q4");
        MvcResult created = postBooking(body).andExpect(status().isCreated()).andReturn();
        String id = json(created).get("id").asText();

        mockMvc.perform(get("/api/bookings/{id}/ics", id).with(auth()))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Disposition", containsString("booking-" + id + ".ics")))
                .andExpect(content().contentTypeCompatibleWith(MediaType.parseMediaType("text/calendar")))
                .andExpect(content().string(containsString("BEGIN:VCALENDAR")))
                .andExpect(content().string(containsString("DTSTART:" + date.toString().replace("-", "")
                        + "T150000")))
                .andExpect(content().string(containsString("SUMMARY:Sync\\, planning\\; Q4")))
                .andExpect(content().string(containsString("END:VCALENDAR")));
    }
}
