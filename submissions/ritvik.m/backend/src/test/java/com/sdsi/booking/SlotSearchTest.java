package com.sdsi.booking;

import com.sdsi.booking.support.IntegrationTestBase;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SlotSearchTest extends IntegrationTestBase {

    @Test
    void returnsTheEarliestFittingRoomAtNine() throws Exception {
        LocalDate date = futureDate();
        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "4")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.start").value(date + "T09:00:00"))
                .andExpect(jsonPath("$.slot.end").value(date + "T10:00:00"))
                .andExpect(jsonPath("$.slot.room.id").value("atlas"))
                .andExpect(jsonPath("$.alternatives.length()").value(4));
    }

    @Test
    void skipsRoomsThatAreAlreadyBusy() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 4);

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "4")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.start").value(date + "T09:00:00"))
                .andExpect(jsonPath("$.slot.room.id").value("orion"));
    }

    @Test
    void roomFilterReturnsTheNextFreeSlotForThatRoom() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(9, 0), date.atTime(10, 0), 2);

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .param("roomId", "atlas")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.start").value(date + "T10:00:00"))
                .andExpect(jsonPath("$.slot.room.id").value("atlas"));
    }

    @Test
    void gridRoundsStartTimesUpAfterAnOffGridBooking() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(9, 10), date.atTime(10, 0), 2);

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .param("roomId", "atlas")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.start").value(date + "T10:00:00"));
    }

    @Test
    void amenitiesAreRequiredWhenRequested() throws Exception {
        LocalDate date = futureDate();
        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "30")
                        .param("attendees", "4")
                        .param("amenities", "projector")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.room.id").value("orion"));

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "30")
                        .param("attendees", "4")
                        .param("amenities", "projector", "speakerphone")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.room.id").value("vega"));
    }

    @Test
    void fullyBookedRoomHasNoSlot() throws Exception {
        LocalDate date = futureDate();
        createBooking("lumen", date.atTime(9, 0), date.atTime(18, 0), 24);

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "24")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot").doesNotExist())
                .andExpect(jsonPath("$.message", containsString("No free")));
    }

    @Test
    void tooManyAttendeesYieldsNoSlot() throws Exception {
        LocalDate date = futureDate();
        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "30")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot").doesNotExist())
                .andExpect(jsonPath("$.message", containsString("No active room")));
    }

    @Test
    void roomSpecificCapacityMessageIsClear() throws Exception {
        LocalDate date = futureDate();
        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "30")
                        .param("attendees", "3")
                        .param("roomId", "kepler")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot").doesNotExist());
    }

    @Test
    void validatingQueryParameters() throws Exception {
        LocalDate date = futureDate();
        mockMvc.perform(get("/api/find-slot")
                        .param("date", LocalDate.now(clock).minusDays(1).toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("DATE_IN_PAST"));

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "5")
                        .param("attendees", "2")
                        .with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_DURATION"));

        mockMvc.perform(get("/api/find-slot")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "0")
                        .with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_ATTENDEES"));
    }

    @Test
    void aliasedPathAndAvailabilityTimelineWork() throws Exception {
        LocalDate date = futureDate();
        createBooking("atlas", date.atTime(10, 0), date.atTime(11, 0), 2);

        mockMvc.perform(get("/api/slots")
                        .param("date", date.toString())
                        .param("durationMinutes", "60")
                        .param("attendees", "2")
                        .param("roomId", "atlas")
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slot.start").value(date + "T09:00:00"));

        mockMvc.perform(get("/api/rooms/atlas/availability")
                        .param("date", date.toString()).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.busy.length()").value(1))
                .andExpect(jsonPath("$.busy[0].start").value(date + "T10:00:00"))
                .andExpect(jsonPath("$.free.length()").value(2))
                .andExpect(jsonPath("$.free[0].start").value(date + "T09:00:00"))
                .andExpect(jsonPath("$.free[0].end").value(date + "T10:00:00"))
                .andExpect(jsonPath("$.free[1].start").value(date + "T11:00:00"))
                .andExpect(jsonPath("$.free[1].minutes").value(420));
    }
}
