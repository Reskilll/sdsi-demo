package com.sdsi.booking;

import com.fasterxml.jackson.databind.JsonNode;
import com.sdsi.booking.support.IntegrationTestBase;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.time.format.DateTimeFormatter;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RecurringBookingTest extends IntegrationTestBase {

    private static final DateTimeFormatter API_TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    @Test
    void createsWeeklySeriesOnTheDefaultWeekday() throws Exception {
        LocalDate monday = nextMonday();
        MvcResult result = createRecurring(recurringPayload("atlas", monday, 4, 4))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.created.length()").value(4))
                .andExpect(jsonPath("$.skipped.length()").value(0))
                .andExpect(jsonPath("$.series.daysOfWeek[0]").value("MONDAY"))
                .andExpect(jsonPath("$.message", containsString("Created 4")))
                .andReturn();

        JsonNode body = json(result);
        assertThat(body.get("seriesId").asText()).isNotBlank();
        JsonNode created = body.get("created");
        for (int week = 0; week < 4; week++) {
            assertThat(created.get(week).get("start").asText())
                    .isEqualTo(monday.plusWeeks(week).atTime(10, 0).format(API_TIME));
            assertThat(created.get(week).get("occurrenceIndex").asInt()).isEqualTo(week + 1);
            assertThat(created.get(week).get("seriesId").asText())
                    .isEqualTo(body.get("seriesId").asText());
        }
        assertThat(bookingRepository.count()).isEqualTo(4);
    }

    @Test
    void supportsMultipleWeekdaysInTheWeekWindow() throws Exception {
        LocalDate monday = nextMonday();
        Map<String, Object> payload = recurringPayload("atlas", monday, 2, 2);
        payload.put("daysOfWeek", List.of("MONDAY", "WEDNESDAY"));

        createRecurring(payload)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.created.length()").value(4))
                .andExpect(jsonPath("$.created[0].start").value(monday.atTime(10, 0).format(API_TIME)))
                .andExpect(jsonPath("$.created[1].start").value(monday.plusDays(2).atTime(10, 0).format(API_TIME)))
                .andExpect(jsonPath("$.created[2].start").value(monday.plusWeeks(1).atTime(10, 0).format(API_TIME)))
                .andExpect(jsonPath("$.created[3].start").value(monday.plusWeeks(1).plusDays(2).atTime(10, 0).format(API_TIME)));
    }

    @Test
    void previewReportsConflictsPerOccurrenceWithoutWriting() throws Exception {
        LocalDate monday = nextMonday();
        JsonNode clash = createBooking("atlas", monday.plusWeeks(1).atTime(10, 30),
                monday.plusWeeks(1).atTime(11, 30), 2);

        previewRecurring(recurringPayload("atlas", monday, 4, 4))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.occurrenceCount").value(4))
                .andExpect(jsonPath("$.conflictCount").value(1))
                .andExpect(jsonPath("$.occurrences[0].status").value("FREE"))
                .andExpect(jsonPath("$.occurrences[1].status").value("CONFLICT"))
                .andExpect(jsonPath("$.occurrences[1].conflicts[0].bookingId").value(clash.get("id").asText()))
                .andExpect(jsonPath("$.occurrences[2].status").value("FREE"));

        assertThat(bookingRepository.count()).isEqualTo(1);
    }

    @Test
    void atomicCreateRejectsTheWholeSeriesAndReportsConflicts() throws Exception {
        LocalDate monday = nextMonday();
        createBooking("atlas", monday.plusWeeks(1).atTime(10, 30),
                monday.plusWeeks(1).atTime(11, 30), 2);

        createRecurring(recurringPayload("atlas", monday, 4, 4))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("RECURRING_CONFLICT"))
                .andExpect(jsonPath("$.totalOccurrences").value(4))
                .andExpect(jsonPath("$.conflictCount").value(1))
                .andExpect(jsonPath("$.occurrences.length()").value(1))
                .andExpect(jsonPath("$.occurrences[0].status").value("CONFLICT"));

        assertThat(bookingRepository.count()).isEqualTo(1);
        assertThat(seriesRepository.count()).isZero();
    }

    @Test
    void skipConflictsCreatesTheFreeOccurrences() throws Exception {
        LocalDate monday = nextMonday();
        createBooking("atlas", monday.plusWeeks(1).atTime(10, 30),
                monday.plusWeeks(1).atTime(11, 30), 2);

        Map<String, Object> payload = recurringPayload("atlas", monday, 4, 4);
        payload.put("skipConflicts", true);

        MvcResult result = createRecurring(payload)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.created.length()").value(3))
                .andExpect(jsonPath("$.skipped.length()").value(1))
                .andExpect(jsonPath("$.message", containsString("3 of 4")))
                .andReturn();

        String seriesId = json(result).get("seriesId").asText();
        mockMvc.perform(get("/api/series/{id}", seriesId).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.occurrences.length()").value(3));

        assertThat(bookingRepository.count()).isEqualTo(4);
    }

    @Test
    void cancellingSeriesOnlyCancelsFutureOccurrences() throws Exception {
        LocalDate monday = nextMonday();
        MvcResult created = createRecurring(recurringPayload("atlas", monday, 3, 2))
                .andExpect(status().isCreated())
                .andReturn();
        String seriesId = json(created).get("seriesId").asText();

        mockMvc.perform(delete("/api/series/{id}", seriesId)
                        .param("from", monday.atTime(0, 0).toString())
                        .with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.cancelledCount").value(3));

        mockMvc.perform(get("/api/series/{id}", seriesId).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.occurrences.length()").value(3))
                .andExpect(jsonPath("$.occurrences[0].status").value("CANCELLED"))
                .andExpect(jsonPath("$.occurrences[2].status").value("CANCELLED"));

        mockMvc.perform(delete("/api/series/{id}", seriesId).with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.cancelledCount").value(0));
    }

    @Test
    void seriesCanBeListedAndFetched() throws Exception {
        LocalDate monday = nextMonday();
        createRecurring(recurringPayload("orion", monday, 2, 3)).andExpect(status().isCreated());

        mockMvc.perform(get("/api/series").with(auth()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1))
                .andExpect(jsonPath("$.content[0].room.id").value("orion"))
                .andExpect(jsonPath("$.content[0].daysOfWeek[0]").value("MONDAY"));

        mockMvc.perform(get("/api/series/{id}", java.util.UUID.randomUUID()).with(auth()))
                .andExpect(status().isNotFound());
    }

    @Test
    void recurrenceValidation() throws Exception {
        LocalDate monday = nextMonday();

        Map<String, Object> zeroWeeks = recurringPayload("atlas", monday, 1, 2);
        zeroWeeks.put("weeks", 0);
        createRecurring(zeroWeeks).andExpect(status().isBadRequest());

        Map<String, Object> outsideHours = recurringPayload("atlas", monday, 2, 2);
        outsideHours.put("startTime", "08:00");
        createRecurring(outsideHours)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("OUTSIDE_OFFICE_HOURS"));

        Map<String, Object> tooMany = recurringPayload("atlas", monday, 2, 9);
        createRecurring(tooMany)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("CAPACITY_EXCEEDED"));

        Map<String, Object> noOccurrence = recurringPayload("atlas", monday.plusDays(1), 1, 2);
        noOccurrence.put("daysOfWeek", List.of("MONDAY"));
        createRecurring(noOccurrence)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("NO_OCCURRENCES"));
    }

    @Test
    void seriesEndpointRejectsInvalidPaging() throws Exception {
        mockMvc.perform(get("/api/series").param("size", "1000").with(auth()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_PAGE_SIZE"));
    }
}
