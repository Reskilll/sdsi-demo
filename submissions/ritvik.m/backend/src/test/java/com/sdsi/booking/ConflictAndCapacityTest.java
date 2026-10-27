package com.sdsi.booking;

import com.fasterxml.jackson.databind.JsonNode;
import com.sdsi.booking.support.IntegrationTestBase;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ConflictAndCapacityTest extends IntegrationTestBase {

    @Test
    void overlappingBookingIsRejectedWithConflictDetails() throws Exception {
        LocalDate date = futureDate();
        JsonNode first = createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 4);

        postBooking(bookingPayload("atlas", date.atTime(10, 30), date.atTime(11, 30), 2))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BOOKING_CONFLICT"))
                .andExpect(jsonPath("$.conflicts.length()").value(1))
                .andExpect(jsonPath("$.conflicts[0].bookingId").value(first.get("id").asText()))
                .andExpect(jsonPath("$.conflicts[0].title").value("Planning"));
    }

    @Test
    void exactDuplicateBookingIsRejected() throws Exception {
        LocalDate date = futureDate();
        var payload = bookingPayload("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);
        postBooking(payload).andExpect(status().isCreated());

        postBooking(payload)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BOOKING_CONFLICT"))
                .andExpect(jsonPath("$.conflicts.length()").value(1));
    }

    @Test
    void fullyContainedAndContainingOverlapsAreRejected() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(10, 0), date.atTime(12, 0), 2);

        postBooking(bookingPayload("atlas", date.atTime(10, 30), date.atTime(11, 0), 2))
                .andExpect(status().isConflict());
        postBooking(bookingPayload("atlas", date.atTime(9, 30), date.atTime(12, 30), 2))
                .andExpect(status().isConflict());
    }

    @Test
    void backToBackBookingsAreAllowed() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);
        createBooking("atlas", date.atTime(11, 0), date.atTime(12, 0), 2);
        createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 2);
    }

    @Test
    void sameTimeInDifferentRoomsIsAllowed() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);
        createBooking("orion", date.atTime(10, 0), date.atTime(11, 0), 2);
    }

    @Test
    void updateCannotOverlapAnotherBooking() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 2);
        JsonNode second = createBooking("atlas", date.atTime(11, 0), date.atTime(12, 0), 2);

        Map<String, Object> moveOntoFirst = bookingPayload("atlas", date.atTime(9, 30), date.atTime(10, 30), 2);
        putBooking(second.get("id").asText(), moveOntoFirst)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BOOKING_CONFLICT"));

        Map<String, Object> renameOnly = bookingPayload("atlas", date.atTime(11, 0), date.atTime(12, 0), 2);
        renameOnly.put("title", "Renamed");
        putBooking(second.get("id").asText(), renameOnly)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Renamed"));
    }

    @Test
    void capacityIsEnforcedFromCountAndFromAttendeeList() throws Exception {
        LocalDate date = futureDate();
        postBooking(bookingPayload("atlas", date.atTime(10, 0), date.atTime(11, 0), 5))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("CAPACITY_EXCEEDED"));

        Map<String, Object> byList = bookingPayload("atlas", date.atTime(10, 0), date.atTime(11, 0), 1);
        byList.remove("attendeeCount");
        byList.put("attendees", List.of("a", "b", "c", "d", "e"));
        postBooking(byList)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("CAPACITY_EXCEEDED"));

        createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 4);
    }

    @Test
    void openingHoursAreEnforced() throws Exception {
        LocalDate date = futureDate();
        postBooking(bookingPayload("atlas", date.atTime(8, 30), date.atTime(9, 30), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("OUTSIDE_OFFICE_HOURS"));

        postBooking(bookingPayload("atlas", date.atTime(17, 30), date.atTime(18, 30), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("OUTSIDE_OFFICE_HOURS"));

        createBooking("atlas", date.atTime(17, 0), date.atTime(18, 0), 2);
        createBooking("atlas", date.atTime(9, 0), date.atTime(9, 15), 1);
    }

    @Test
    void invalidIntervalsAndDurationsAreRejected() throws Exception {
        LocalDate date = futureDate();
        postBooking(bookingPayload("atlas", date.atTime(10, 0), date.atTime(10, 0), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_INTERVAL"));

        postBooking(bookingPayload("atlas", date.atTime(10, 0), date.atTime(9, 0), 2))
                .andExpect(status().isBadRequest());

        postBooking(bookingPayload("atlas", date.atTime(10, 0), date.atTime(10, 10), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_DURATION"));

        postBooking(bookingPayload("atlas", date.atTime(23, 0), date.plusDays(1).atTime(1, 0), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_INTERVAL"));

        postBooking(bookingPayload("atlas", date.atTime(10, 0, 30), date.atTime(11, 0, 30), 2))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_INTERVAL"));
    }

    @Test
    void unknownRoomIsNotFound() throws Exception {
        LocalDate date = futureDate();
        postBooking(bookingPayload("nope", date.atTime(10, 0), date.atTime(11, 0), 2))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void listCanFilterByStatusAndTimeRange() throws Exception {
        LocalDate date = futureDate();
        JsonNode cancelled = createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 2);
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .patch("/api/bookings/{id}/cancel", cancelled.get("id").asText()).with(auth()))
                .andExpect(status().isOk());
        createBooking("atlas", date.atTime(11, 0), date.atTime(12, 0), 2);

        mockMvc.perform(get("/api/bookings").param("status", "CANCELLED").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1));

        mockMvc.perform(get("/api/bookings")
                        .param("from", date.atTime(10, 30).toString())
                        .param("to", date.atTime(13, 0).toString())
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1))
                .andExpect(jsonPath("$.content[0].start").value(date + "T11:00:00"));
    }
}
