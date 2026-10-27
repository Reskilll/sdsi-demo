package com.sdsi.booking;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.web.dto.BookingDtos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * M1–M5 and the analytics stretch goal, exercised through the REST layer against a real
 * H2 database. Each test rolls back, so seeded rooms stay pristine.
 *
 * <p>Reference week: Monday {@value #MONDAY}. All instants are UTC.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class BookingApiIntegrationTest {

    private static final LocalDate MONDAY = LocalDate.of(2026, 11, 2);
    private static final LocalDate TUESDAY = LocalDate.of(2026, 11, 3);
    private static final LocalDate SATURDAY = LocalDate.of(2026, 11, 7);

    @Autowired
    private MockMvc mvc;

    @Autowired
    private ObjectMapper json;

    @Autowired
    private RoomRepository rooms;

    @Autowired
    private BookingRepository bookings;

    private Room roomA;
    private Room roomB;

    @BeforeEach
    void resolveRooms() {
        roomA = rooms.findByName("Room A").orElseThrow();
        roomB = rooms.findByName("Room B").orElseThrow();
    }

    // ------------------------------------------------------------------ M1 CRUD

    @Test
    @DisplayName("M1: creating a booking returns 201 with a Location header and the full payload")
    void createBooking_returns201_andEchoesPayload() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                List.of("dev-1", "dev-2"))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.roomId").value(roomA.getId()))
                .andExpect(jsonPath("$.roomName").value("Room A"))
                .andExpect(jsonPath("$.organiser").value("Priya"))
                .andExpect(jsonPath("$.attendees[1]").value("dev-2"))
                .andExpect(jsonPath("$.startTime").value("2026-11-02T09:00:00Z"));
    }

    @Test
    @DisplayName("M1: a booking can be fetched, rescheduled and deleted")
    void crudLifecycle() throws Exception {
        String created = mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0), List.of("a"))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        long id = json.readTree(created).get("id").asLong();

        mvc.perform(get("/api/bookings/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.organiser").value("Priya"));

        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 14, 0), at(MONDAY, 15, 0), List.of("a"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.startTime").value("2026-11-02T14:00:00Z"));

        mvc.perform(delete("/api/bookings/{id}", id)).andExpect(status().isNoContent());
        mvc.perform(get("/api/bookings/{id}", id)).andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("M1: an unknown booking id is a 404, not a 500")
    void unknownBooking_is404() throws Exception {
        mvc.perform(get("/api/bookings/{id}", 999_999)).andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("M1: GET /api/rooms exposes the seeded inventory with capacities")
    void rooms_areSeeded() throws Exception {
        mvc.perform(get("/api/rooms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3))
                .andExpect(jsonPath("$[0].name").value("Room A"))
                .andExpect(jsonPath("$[0].capacity").value(5))
                .andExpect(jsonPath("$[2].name").value("Room C"))
                .andExpect(jsonPath("$[2].capacity").value(20));
    }

    // ------------------------------------------------------------------ M2 overlap

    @Test
    @DisplayName("M2: back-to-back bookings 09:00-10:00 then 10:00-11:00 are both accepted")
    void backToBackBookings_areAllowed() throws Exception {
        create(roomA, at(MONDAY, 9, 0), at(MONDAY, 10, 0));

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Arun", at(MONDAY, 10, 0), at(MONDAY, 11, 0), List.of("b"))))
                .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("M2: a booking that ends exactly when another starts is not a conflict")
    void bookingEndingAtExistingStart_isAllowed() throws Exception {
        create(roomA, at(MONDAY, 10, 0), at(MONDAY, 11, 0));

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Arun", at(MONDAY, 9, 0), at(MONDAY, 10, 0), List.of("b"))))
                .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("M2: partial, full and containing overlaps are all rejected with 409")
    void overlappingBookings_areRejected() throws Exception {
        create(roomA, at(MONDAY, 10, 0), at(MONDAY, 11, 0));

        assertConflict(at(MONDAY, 10, 30), at(MONDAY, 11, 30), "partial overlap at the end");
        assertConflict(at(MONDAY, 9, 30), at(MONDAY, 10, 30), "partial overlap at the start");
        assertConflict(at(MONDAY, 10, 15), at(MONDAY, 10, 45), "fully inside");
        assertConflict(at(MONDAY, 9, 0), at(MONDAY, 12, 0), "fully containing");
        assertConflict(at(MONDAY, 10, 0), at(MONDAY, 11, 0), "identical window");
    }

    @Test
    @DisplayName("M2: the same window in a different room is free")
    void overlapIsScopedToRoom() throws Exception {
        create(roomA, at(MONDAY, 10, 0), at(MONDAY, 11, 0));

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomB.getId(), "Arun", at(MONDAY, 10, 0), at(MONDAY, 11, 0), List.of("b"))))
                .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("M2: the conflict response names the blocking booking")
    void conflictResponse_listsBlockers() throws Exception {
        create(roomA, at(MONDAY, 10, 0), at(MONDAY, 11, 0));

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Arun", at(MONDAY, 10, 30), at(MONDAY, 11, 30), List.of("b"))))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.status").value(409))
                .andExpect(jsonPath("$.message").value("Room A is already booked during the requested window"))
                .andExpect(jsonPath("$.details[0]").exists());
    }

    @Test
    @DisplayName("M2: a reschedule may not collide with another booking")
    void reschedule_rejectsCollision() throws Exception {
        long first = create(roomA, at(MONDAY, 9, 0), at(MONDAY, 10, 0));
        long second = create(roomA, at(MONDAY, 11, 0), at(MONDAY, 12, 0));

        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", second)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Arun", at(MONDAY, 9, 30), at(MONDAY, 10, 30), List.of("b"))))
                .andExpect(status().isConflict());

        // Moving onto its own window must not conflict with itself.
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .put("/api/bookings/{id}", first)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0), List.of("a"))))
                .andExpect(status().isOk());
    }

    // ------------------------------------------------------------------ M3 capacity

    @Test
    @DisplayName("M3: attendees beyond capacity are rejected with 400 and a clear message")
    void capacityExceeded_is400() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                List.of("1", "2", "3", "4", "5", "6"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value("attendees (6) exceed Room A capacity (5)"));
    }

    @Test
    @DisplayName("M3: exactly at capacity is allowed")
    void capacityExactlyMet_isAllowed() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                List.of("1", "2", "3", "4", "5"))))
                .andExpect(status().isCreated());
    }

    // ------------------------------------------------------------- window validation

    @Test
    @DisplayName("Validation: endTime must be after startTime")
    void invalidWindow_is400() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 10, 0), at(MONDAY, 10, 0), List.of("a"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("request validation failed"));
    }

    @Test
    @DisplayName("Validation: bookings outside 09:00-18:00 UTC or on weekends are rejected")
    void outsideBusinessHours_is400() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 8, 0), at(MONDAY, 9, 0), List.of("a"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("booking must fall inside 09:00-18:00 UTC on a single weekday"));

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(MONDAY, 17, 30), at(MONDAY, 18, 30), List.of("a"))))
                .andExpect(status().isBadRequest());

        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Priya", at(SATURDAY, 9, 0), at(SATURDAY, 10, 0), List.of("a"))))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("Validation: a non-existent room is a 404")
    void unknownRoom_is404() throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(4242L, "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0), List.of("a"))))
                .andExpect(status().isNotFound());
    }

    // ------------------------------------------------------------------ M4 find-slot

    @Test
    @DisplayName("M4: the earliest slot comes from the smallest room that fits the group")
    void findSlot_prefersBestFitRoom() throws Exception {
        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "4").param("date", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roomName").value("Room A"))
                .andExpect(jsonPath("$.roomCapacity").value(5))
                .andExpect(jsonPath("$.startTime").value("2026-11-02T09:00:00Z"))
                .andExpect(jsonPath("$.endTime").value("2026-11-02T10:00:00Z"));
    }

    @Test
    @DisplayName("M4: a large group skips the small rooms entirely")
    void findSlot_largeGroupGetsLargeRoom() throws Exception {
        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "12").param("date", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roomName").value("Room C"))
                .andExpect(jsonPath("$.roomCapacity").value(20));
    }

    @Test
    @DisplayName("M4: when the best-fit room is busy, the next compliant room is used")
    void findSlot_fallsThroughToNextRoom() throws Exception {
        create(roomA, at(MONDAY, 9, 0), at(MONDAY, 18, 0));

        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "4").param("date", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roomName").value("Room B"));
    }

    @Test
    @DisplayName("M4: the search resumes after an occupied morning block")
    void findSlot_returnsFirstGapAfterExistingBookings() throws Exception {
        create(roomA, at(MONDAY, 9, 0), at(MONDAY, 11, 0));

        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "90").param("attendeeCount", "4").param("date", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.startTime").value("2026-11-02T11:00:00Z"))
                .andExpect(jsonPath("$.endTime").value("2026-11-02T12:30:00Z"));
    }

    @Test
    @DisplayName("M4: the slot never spills past the 18:00 close")
    void findSlot_neverSpillsPastClose() throws Exception {
        create(roomA, at(MONDAY, 9, 0), at(MONDAY, 17, 30));

        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "4").param("date", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.endTime").value("2026-11-02T10:00:00Z"))
                .andExpect(jsonPath("$.roomName").value("Room B"));
    }

    @Test
    @DisplayName("M4: an impossible request is a 404 with an actionable message")
    void findSlot_noAvailability_is404() throws Exception {
        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "4").param("date", SATURDAY.toString()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value(
                        "no availability on 2026-11-07: the office is closed at weekends"));

        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "600").param("attendeeCount", "4").param("date", MONDAY.toString()))
                .andExpect(status().isBadRequest());

        mvc.perform(get("/api/bookings/find-slot")
                        .param("duration", "60").param("attendeeCount", "50").param("date", MONDAY.toString()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("no room has capacity for 50 attendees"));
    }

    // ------------------------------------------------- M5 recurrence dry-run / commit

    @Nested
    @DisplayName("M5: weekly recurrence")
    class Recurrence {

        @Test
        @DisplayName("Step 1: the dry-run reports per-date availability and saves nothing")
        void dryRun_reportsAvailabilityPerDate() throws Exception {
            create(roomB, at(MONDAY, 14, 0), at(MONDAY, 15, 0));
            long before = bookings.count();

            mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "4")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(MONDAY, 14, 0), at(MONDAY, 15, 0),
                                    List.of("a", "b"))))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.requestedOccurrences").value(4))
                    .andExpect(jsonPath("$.availableCount").value(3))
                    .andExpect(jsonPath("$.conflictCount").value(1))
                    .andExpect(jsonPath("$.allAvailable").value(false))
                    .andExpect(jsonPath("$.executable").value(true))
                    .andExpect(jsonPath("$.planToken").isNotEmpty())
                    .andExpect(jsonPath("$.commitEndpoint").value("/api/bookings/recurring/confirm"))
                    .andExpect(jsonPath("$.occurrences[0].available").value(false))
                    .andExpect(jsonPath("$.occurrences[0].reason").value(
                            org.hamcrest.Matchers.containsString("conflicts with")))
                    .andExpect(jsonPath("$.occurrences[1].available").value(true))
                    .andExpect(jsonPath("$.occurrences[1].startTime").value("2026-11-09T14:00:00Z"))
                    .andExpect(jsonPath("$.occurrences[3].available").value(true));

            assertThat(bookings.count()).isEqualTo(before);
        }

        @Test
        @DisplayName("Step 1: a fully blocked series is not executable and issues no token")
        void dryRun_allBlocked_isNotExecutable() throws Exception {
            create(roomB, at(MONDAY, 14, 0), at(MONDAY, 15, 0));

            mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "1")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(MONDAY, 14, 0), at(MONDAY, 15, 0),
                                    List.of("a"))))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.executable").value(false))
                    .andExpect(jsonPath("$.planToken").doesNotExist())
                    .andExpect(jsonPath("$.availableCount").value(0));
        }

        @Test
        @DisplayName("Step 2: confirming the plan saves only the available slots")
        void commit_savesOnlyAvailableSlots() throws Exception {
            create(roomB, at(MONDAY, 14, 0), at(MONDAY, 15, 0));
            long before = bookings.count();

            String dryRun = mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "4")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(MONDAY, 14, 0), at(MONDAY, 15, 0),
                                    List.of("a", "b"))))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            String token = json.readTree(dryRun).get("planToken").asText();

            mvc.perform(post("/api/bookings/recurring/confirm")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(commitBody(token, null)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.savedCount").value(3))
                    .andExpect(jsonPath("$.skippedCount").value(0))
                    .andExpect(jsonPath("$.savedBookings[0].startTime").value("2026-11-09T14:00:00Z"))
                    .andExpect(jsonPath("$.savedBookings[2].startTime").value("2026-11-23T14:00:00Z"));

            assertThat(bookings.count()).isEqualTo(before + 3);

            List<OffsetDateTime> starts = bookings.findByRoom_IdOrderByStartTimeAsc(roomB.getId()).stream()
                    .map(Booking::getStartTime)
                    .toList();
            assertThat(starts).contains(at(MONDAY, 14, 0), at(MONDAY.plusWeeks(1), 14, 0),
                    at(MONDAY.plusWeeks(2), 14, 0), at(MONDAY.plusWeeks(3), 14, 0));
        }

        @Test
        @DisplayName("Step 2: the client may commit only a chosen subset of the available slots")
        void commit_honoursSubsetSelection() throws Exception {
            String dryRun = mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "3")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(TUESDAY, 10, 0), at(TUESDAY, 11, 0),
                                    List.of("a"))))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            var node = json.readTree(dryRun);
            String token = node.get("planToken").asText();

            String subset = """
                    {"planToken":"%s","occurrences":[%s]}
                    """.formatted(token, node.get("occurrences").get(0).toString());

            mvc.perform(post("/api/bookings/recurring/confirm")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(subset))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.savedCount").value(1))
                    .andExpect(jsonPath("$.savedBookings[0].startTime").value("2026-11-03T10:00:00Z"));
        }

        @Test
        @DisplayName("Step 2: a slot booked between dry-run and confirm is skipped, not double-booked")
        void commit_revalidatesAgainstLiveData() throws Exception {
            String dryRun = mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "2")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(TUESDAY, 10, 0), at(TUESDAY, 11, 0),
                                    List.of("a"))))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            String token = json.readTree(dryRun).get("planToken").asText();

            // Someone grabs the second week before the organiser confirms.
            create(roomB, at(TUESDAY.plusWeeks(1), 10, 0), at(TUESDAY.plusWeeks(1), 11, 0));

            mvc.perform(post("/api/bookings/recurring/confirm")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(commitBody(token, null)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.savedCount").value(1))
                    .andExpect(jsonPath("$.skippedCount").value(1))
                    .andExpect(jsonPath("$.skipped[0].startTime").value("2026-11-10T10:00:00Z"));
        }

        @Test
        @DisplayName("Step 2: a tampered token is rejected with 400")
        void commit_rejectsTamperedToken() throws Exception {
            String dryRun = mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "2")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(TUESDAY, 10, 0), at(TUESDAY, 11, 0),
                                    List.of("a"))))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            String token = json.readTree(dryRun).get("planToken").asText();
            String forged = token.substring(0, token.indexOf('.')) + ".AAAA";

            mvc.perform(post("/api/bookings/recurring/confirm")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(commitBody(forged, null)))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("planToken signature is invalid"));
        }

        @Test
        @DisplayName("Step 1: recurrence beyond a year of weeks is rejected")
        void dryRun_rejectsTooManyOccurrences() throws Exception {
            mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "99")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(TUESDAY, 10, 0), at(TUESDAY, 11, 0),
                                    List.of("a"))))
                    .andExpect(status().isBadRequest());
        }
    }

    // ------------------------------------------------------------------ analytics

    @Test
    @DisplayName("Analytics: utilization is booked minutes over bookable weekday minutes")
    void utilization_isComputedOverTheWorkingWeek() throws Exception {
        create(roomA, at(TUESDAY, 9, 0), at(TUESDAY, 10, 30));   // 90 minutes
        create(roomB, at(TUESDAY, 9, 0), at(TUESDAY, 18, 0));    // full bookable day

        mvc.perform(get("/api/analytics/utilization").param("weekStart", MONDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.from").value("2026-11-02T09:00:00Z"))
                .andExpect(jsonPath("$.to").value("2026-11-09T09:00:00Z"))
                .andExpect(jsonPath("$.workingHoursPerDay").value(540))
                .andExpect(jsonPath("$.rooms[0].roomName").value("Room A"))
                .andExpect(jsonPath("$.rooms[0].bookedMinutes").value(90))
                .andExpect(jsonPath("$.rooms[0].availableMinutes").value(2700))
                .andExpect(jsonPath("$.rooms[0].utilizationPercent").value(3.33))
                .andExpect(jsonPath("$.rooms[1].roomName").value("Room B"))
                .andExpect(jsonPath("$.rooms[1].utilizationPercent").value(20.0))
                .andExpect(jsonPath("$.rooms[2].utilizationPercent").value(0.0));
    }

    @Test
    @DisplayName("Analytics: a mid-week date is normalised back to its Monday")
    void utilization_normalisesToMonday() throws Exception {
        create(roomA, at(TUESDAY, 9, 0), at(TUESDAY, 10, 0));

        mvc.perform(get("/api/analytics/utilization").param("weekStart", TUESDAY.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.from").value("2026-11-02T09:00:00Z"))
                .andExpect(jsonPath("$.rooms[0].bookedMinutes").value(60));
    }

    // ------------------------------------------------------ audit: time boundaries

    @Nested
    @DisplayName("Time boundaries")
    class TimeBoundaries {

        @Test
        @DisplayName("A slot ending exactly at 18:00 is valid")
        void slotEndingExactlyAtClose_isValid() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Late", at(MONDAY, 17, 0), at(MONDAY, 18, 0), List.of("a"))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.endTime").value("2026-11-02T18:00:00Z"));
        }

        @Test
        @DisplayName("A slot starting exactly at 09:00 is valid; one ending at 09:00 is not")
        void dayOpenBoundary() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Early", at(MONDAY, 9, 0), at(MONDAY, 9, 30), List.of("a"))))
                    .andExpect(status().isCreated());
        }

        @Test
        @DisplayName("Find-slot offers 17:00-18:00 as the last possible window")
        void findSlot_lastPossibleWindowIs17to18() throws Exception {
            create(roomA, at(MONDAY, 9, 0), at(MONDAY, 17, 0));

            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "60").param("attendeeCount", "4").param("date", MONDAY.toString()))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.startTime").value("2026-11-02T17:00:00Z"))
                    .andExpect(jsonPath("$.endTime").value("2026-11-02T18:00:00Z"));
        }

        @Test
        @DisplayName("Find-slot never offers a window that spills past 18:00")
        void findSlot_neverOffersPastClose() throws Exception {
            // Room A is free from 17:00, but only 60 minutes remain before close.
            create(roomA, at(MONDAY, 9, 0), at(MONDAY, 17, 0));

            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "90").param("attendeeCount", "4").param("date", MONDAY.toString()))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.roomName").value("Room B"))
                    .andExpect(jsonPath("$.startTime").value("2026-11-02T09:00:00Z"));

            String body = mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "30").param("attendeeCount", "4").param("date", MONDAY.toString()))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            assertThat(json.readTree(body).get("endTime").asText()).isLessThanOrEqualTo("2026-11-02T18:00:00Z");
        }

        @Test
        @DisplayName("Find-slot accepts a duration that exactly fills the day")
        void findSlot_fullDayDuration_isExact() throws Exception {
            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "540").param("attendeeCount", "1").param("date", MONDAY.toString()))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.startTime").value("2026-11-02T09:00:00Z"))
                    .andExpect(jsonPath("$.endTime").value("2026-11-02T18:00:00Z"));
        }

        @Test
        @DisplayName("A slot straddling midnight is rejected as outside working hours")
        void slotStraddlingMidnight_isRejected() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Night", at(MONDAY, 23, 0), at(TUESDAY, 1, 0), List.of("a"))))
                    .andExpect(status().isBadRequest());
        }
    }

    // ------------------------------------------------------ audit: timezone integrity

    @Nested
    @DisplayName("Timezone integrity")
    class TimezoneIntegrity {

        @Test
        @DisplayName("Instants are normalised to UTC on the way out")
        void offsets_areNormalisedToUtc() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", "2026-11-02T14:30:00+05:30",
                                    "2026-11-02T15:30:00+05:30", List.of("a"))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.startTime").value("2026-11-02T09:00:00Z"))
                    .andExpect(jsonPath("$.endTime").value("2026-11-02T10:00:00Z"));
        }

        @Test
        @DisplayName("The same instant expressed in another offset still collides (no silent bypass)")
        void equivalentInstantsInDifferentOffsets_collide() throws Exception {
            create(roomA, at(MONDAY, 9, 0), at(MONDAY, 10, 0));

            // 14:30+05:30 and 09:00Z are the same moment.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Arun", "2026-11-02T14:30:00+05:30",
                                    "2026-11-02T15:30:00+05:30", List.of("b"))))
                    .andExpect(status().isConflict());
        }

        @Test
        @DisplayName("Working hours are evaluated in UTC, not the caller's offset")
        void workingHours_areEvaluatedInUtc() throws Exception {
            // 08:00Z is before opening, even though it is 13:30 in +05:30.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", "2026-11-02T08:00:00Z", "2026-11-02T09:00:00Z",
                                    List.of("a"))))
                    .andExpect(status().isBadRequest());

            // 13:30+05:30 == 08:00Z, so it must be rejected too.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", "2026-11-02T13:30:00+05:30",
                                    "2026-11-02T14:30:00+05:30", List.of("a"))))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("A negative offset that lands on the previous UTC day is rejected")
        void negativeOffsetCrossingUtcDay_isRejected() throws Exception {
            // 2026-11-02T04:00-06:00 == 10:00Z, a valid weekday window.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", "2026-11-02T04:00:00-06:00",
                                    "2026-11-02T05:00:00-06:00", List.of("a"))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.startTime").value("2026-11-02T10:00:00Z"));

            // 2026-11-01T23:00-06:00 == 2026-11-02T05:00Z: still before opening on Monday.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", "2026-11-01T23:00:00-06:00",
                                    "2026-11-02T00:00:00-06:00", List.of("a"))))
                    .andExpect(status().isBadRequest());
        }
    }

    // ------------------------------------------------------ audit: input validation

    @Nested
    @DisplayName("Malformed input")
    class MalformedInput {

        @Test
        @DisplayName("A missing or blank organiser is a 400 with a field-level detail")
        void organiser_isRequired() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"roomId":%d,"organiser":"  ","startTime":"2026-11-02T09:00:00Z",
                                     "endTime":"2026-11-02T10:00:00Z","attendees":["a"]}
                                    """.formatted(roomA.getId())))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("request validation failed"))
                    .andExpect(jsonPath("$.details[0]").value("organiser: organiser is required"));
        }

        @Test
        @DisplayName("A missing roomId or startTime is a 400")
        void requiredFields_areEnforced() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"organiser":"Priya","startTime":"2026-11-02T09:00:00Z",
                                     "endTime":"2026-11-02T10:00:00Z","attendees":["a"]}
                                    """))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value("roomId: roomId is required"));

            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"roomId":1,"organiser":"Priya","endTime":"2026-11-02T10:00:00Z","attendees":["a"]}
                                    """))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value("startTime: startTime is required"));
        }

        @Test
        @DisplayName("An empty or absent attendees list is a 400")
        void attendees_isRequired() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"roomId":%d,"organiser":"Priya","startTime":"2026-11-02T09:00:00Z",
                                     "endTime":"2026-11-02T10:00:00Z","attendees":[]}
                                    """.formatted(roomA.getId())))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value(
                            "attendees: attendees must contain at least one attendee"));

            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"roomId":%d,"organiser":"Priya","startTime":"2026-11-02T09:00:00Z",
                                     "endTime":"2026-11-02T10:00:00Z"}
                                    """.formatted(roomA.getId())))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("A blank attendee entry is a 400")
        void blankAttendee_isRejected() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    java.util.Arrays.asList("dev-1", "   "))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("request validation failed"));
        }

        @Test
        @DisplayName("An over-long organiser or attendee value is a 400")
        void oversizedStrings_areRejected() throws Exception {
            String tooLong = "x".repeat(129);
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), tooLong, at(MONDAY, 9, 0), at(MONDAY, 10, 0), List.of("a"))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value(
                            "organiser: organiser must not exceed 128 characters"));

            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    List.of(tooLong))))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("A past startTime is a 400")
        void pastStartTime_isRejected() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(LocalDate.of(2020, 1, 6), 9, 0),
                                    at(LocalDate.of(2020, 1, 6), 10, 0), List.of("a"))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value(
                            "startTime: startTime must be today or in the future"));
        }

        @Test
        @DisplayName("A malformed timestamp is a 400, not a 500")
        void malformedTimestamp_is400() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"roomId":%d,"organiser":"Priya","startTime":"not-a-timestamp",
                                     "endTime":"2026-11-02T10:00:00Z","attendees":["a"]}
                                    """.formatted(roomA.getId())))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.status").value(400))
                    .andExpect(jsonPath("$.message").value(
                            "request body is malformed or contains an invalid value"))
                    .andExpect(jsonPath("$.details[0]").value(
                            org.hamcrest.Matchers.containsString("startTime")));
        }

        @Test
        @DisplayName("Broken JSON is a 400, not a 500")
        void unparseableJson_is400() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"roomId\":1,"))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("A missing find-slot parameter or bad date is a 400")
        void findSlot_badParameters_are400() throws Exception {
            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "60").param("attendeeCount", "4"))
                    .andExpect(status().isBadRequest());

            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "60").param("attendeeCount", "4").param("date", "02-11-2026"))
                    .andExpect(status().isBadRequest());

            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "0").param("attendeeCount", "4").param("date", MONDAY.toString()))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("duration must be >= 1 minute"));

            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "60").param("attendeeCount", "0").param("date", MONDAY.toString()))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("attendeeCount must be >= 1"));
        }

        @Test
        @DisplayName("Find-slot rejects a date in the past")
        void findSlot_pastDate_is400() throws Exception {
            mvc.perform(get("/api/bookings/find-slot")
                            .param("duration", "60").param("attendeeCount", "4")
                            .param("date", LocalDate.now(java.time.ZoneOffset.UTC).minusDays(1).toString()))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("date must be today or in the future"));
        }

        @Test
        @DisplayName("A commit request without a planToken is a 400")
        void commit_requiresToken() throws Exception {
            mvc.perform(post("/api/bookings/recurring/confirm")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"occurrences\":[]}"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.details[0]").value("planToken: planToken is required"));
        }
    }

    // ------------------------------------------------------ audit: duplicate attendees

    @Nested
    @DisplayName("Duplicate attendees")
    class DuplicateAttendees {

        @Test
        @DisplayName("An exact duplicate attendee is a 400 naming the offender")
        void exactDuplicate_isRejected() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    List.of("dev@example.com", "dev@example.com"))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value(
                            "attendees must be unique; duplicated: dev@example.com"));
        }

        @Test
        @DisplayName("Duplicates differing only by case or surrounding whitespace are still rejected")
        void caseAndWhitespaceDuplicates_areRejected() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    List.of("Dev@Example.com", " dev@example.com "))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value(
                            "attendees must be unique; duplicated: dev@example.com"));
        }

        @Test
        @DisplayName("Duplicates are caught before the capacity check, so they never inflate the count")
        void duplicatesAreRejectedEvenWhenWithinCapacity() throws Exception {
            // Room A seats 5; four entries with one repeat is really a group of three.
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    List.of("a", "b", "c", "c"))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("attendees must be unique; duplicated: c"));
        }

        @Test
        @DisplayName("Distinct attendees are stored trimmed and de-duplicated in order")
        void distinctAttendees_areStoredTrimmed() throws Exception {
            mvc.perform(post("/api/bookings")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomA.getId(), "Priya", at(MONDAY, 9, 0), at(MONDAY, 10, 0),
                                    List.of(" dev-1 ", "Dev-2"))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.attendees[0]").value("dev-1"))
                    .andExpect(jsonPath("$.attendees[1]").value("Dev-2"));
        }

        @Test
        @DisplayName("The recurrence dry-run applies the same duplicate rule")
        void dryRun_rejectsDuplicateAttendees() throws Exception {
            mvc.perform(post("/api/bookings/recurring/dry-run")
                            .param("occurrences", "2")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(booking(roomB.getId(), "Standup", at(TUESDAY, 10, 0), at(TUESDAY, 11, 0),
                                    List.of("a", "A"))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.message").value("attendees must be unique; duplicated: A"));
        }
    }

    // ---------------------------------------------------------------- helpers

    private String booking(Long roomId, String organiser, OffsetDateTime start, OffsetDateTime end,
                           List<String> attendees) throws Exception {
        return json.writeValueAsString(new BookingDtos.BookingRequest(roomId, organiser, start, end, attendees));
    }

    /** Raw ISO strings, for tests that need to control the offset explicitly. */
    private String booking(Long roomId, String organiser, String start, String end, List<String> attendees) {
        return """
                {"roomId":%d,"organiser":"%s","startTime":"%s","endTime":"%s","attendees":%s}
                """.formatted(roomId, organiser, start, end,
                attendees.stream().map(a -> "\"" + a + "\"").collect(java.util.stream.Collectors.joining(",", "[", "]")));
    }

    private String commitBody(String token, String occurrences) {
        return occurrences == null
                ? "{\"planToken\":\"%s\"}".formatted(token)
                : "{\"planToken\":\"%s\",\"occurrences\":%s}".formatted(token, occurrences);
    }

    private long create(Room room, OffsetDateTime start, OffsetDateTime end) throws Exception {
        String body = mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(room.getId(), "Fixture", start, end, List.of("fixture"))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("id").asLong();
    }

    private void assertConflict(OffsetDateTime start, OffsetDateTime end, String scenario) throws Exception {
        mvc.perform(post("/api/bookings")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(booking(roomA.getId(), "Arun", start, end, List.of("b"))))
                .andExpect(status().isConflict());
        assertThat(bookings.findOverlapping(roomA.getId(), start, end)).as(scenario).isNotEmpty();
    }

    private static OffsetDateTime at(LocalDate date, int hour, int minute) {
        return date.atTime(hour, minute).atOffset(ZoneOffset.UTC);
    }
}
