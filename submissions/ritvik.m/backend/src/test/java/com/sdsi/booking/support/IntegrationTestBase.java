package com.sdsi.booking.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.booking.repo.BookingRepository;
import com.sdsi.booking.repo.BookingSeriesRepository;
import com.sdsi.booking.repo.RoomRepository;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.TemporalAdjusters;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public abstract class IntegrationTestBase {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected ObjectMapper objectMapper;

    @Autowired
    protected BookingRepository bookingRepository;

    @Autowired
    protected BookingSeriesRepository seriesRepository;

    @Autowired
    protected RoomRepository roomRepository;

    @Autowired
    protected Clock clock;

    @BeforeEach
    void cleanDatabase() {
        bookingRepository.deleteAll();
        seriesRepository.deleteAll();
    }

    protected RequestPostProcessor auth() {
        return SecurityMockMvcRequestPostProcessors.httpBasic("test", "test-password");
    }

    protected LocalDate futureDate() {
        return LocalDate.now(clock).plusWeeks(4);
    }

    protected LocalDate nextMonday() {
        return LocalDate.now(clock).plusWeeks(2)
                .with(TemporalAdjusters.nextOrSame(DayOfWeek.MONDAY));
    }

    protected Map<String, Object> bookingPayload(String roomId, LocalDateTime start, LocalDateTime end,
                                                 int attendees) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("roomId", roomId);
        body.put("organiser", "Ritvik");
        body.put("organiserEmail", "Ritvik@Example.com");
        body.put("title", "Planning");
        body.put("description", "Sprint planning");
        body.put("start", start.toString());
        body.put("end", end.toString());
        body.put("attendeeCount", attendees);
        return body;
    }

    protected ResultActions postBooking(Object body) throws Exception {
        return mockMvc.perform(jsonRequest(post("/api/bookings"), body));
    }

    protected ResultActions putBooking(Object id, Object body) throws Exception {
        return mockMvc.perform(jsonRequest(put("/api/bookings/{id}", id), body));
    }

    protected MockHttpServletRequestBuilder jsonRequest(MockHttpServletRequestBuilder builder, Object body)
            throws Exception {
        return builder.with(auth())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(body));
    }

    protected JsonNode json(MvcResult result) throws Exception {
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    protected JsonNode createBooking(String roomId, LocalDateTime start, LocalDateTime end, int attendees)
            throws Exception {
        MvcResult result = postBooking(bookingPayload(roomId, start, end, attendees))
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isCreated())
                .andReturn();
        return json(result);
    }

    protected ResultActions previewRecurring(Object body) throws Exception {
        return mockMvc.perform(jsonRequest(post("/api/bookings/recurring/preview"), body));
    }

    protected ResultActions createRecurring(Object body) throws Exception {
        return mockMvc.perform(jsonRequest(post("/api/bookings/recurring"), body));
    }

    protected Map<String, Object> recurringPayload(String roomId, LocalDate startsOn, int weeks,
                                                   int attendees) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("roomId", roomId);
        body.put("organiser", "Ritvik");
        body.put("title", "Weekly sync");
        body.put("startsOn", startsOn.toString());
        body.put("startTime", "10:00");
        body.put("endTime", "11:00");
        body.put("weeks", weeks);
        body.put("attendeeCount", attendees);
        return body;
    }
}
