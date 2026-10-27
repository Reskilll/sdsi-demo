package com.sdsi.booking;

import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.service.AttendeeRules;
import com.sdsi.booking.service.BookingService;
import com.sdsi.booking.web.dto.BookingDtos;
import com.sdsi.booking.web.error.ApiException;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Guards the service layer directly: bean-validation annotations never run for a
 * programmatic caller, so these invariants must hold without the web layer.
 */
@SpringBootTest
@Transactional
class ServiceGuardTest {

    private static final LocalDate MONDAY = LocalDate.of(2026, 11, 2);

    @Autowired
    private BookingService service;

    @Autowired
    private RoomRepository rooms;

    @Test
    @DisplayName("AttendeeRules trims, preserves order and rejects case-insensitive duplicates")
    void attendeeRules_areEnforced() {
        assertThat(AttendeeRules.normalise(List.of(" dev-1 ", "Dev-2"))).containsExactly("dev-1", "Dev-2");
        assertThatThrownBy(() -> AttendeeRules.normalise(List.of("a", "A")))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("attendees must be unique; duplicated: A");
        assertThatThrownBy(() -> AttendeeRules.normalise(List.of()))
                .isInstanceOf(ApiException.BadRequest.class);
        assertThatThrownBy(() -> AttendeeRules.normalise(java.util.Collections.singletonList(null)))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("attendees must not contain blank entries");
    }

    @Test
    @DisplayName("A null roomId is rejected rather than throwing a NullPointerException")
    void nullRoomId_is400() {
        BookingDtos.BookingRequest request = new BookingDtos.BookingRequest(
                null, "Priya", at(9, 0), at(10, 0), List.of("a"));

        assertThatThrownBy(() -> service.create(request))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("roomId is required");
    }

    @Test
    @DisplayName("Null start/end timestamps are rejected rather than throwing a NullPointerException")
    void nullTimestamps_are400() {
        Room room = rooms.findByName("Room A").orElseThrow();
        BookingDtos.BookingRequest missingStart = new BookingDtos.BookingRequest(
                room.getId(), "Priya", null, at(10, 0), List.of("a"));
        BookingDtos.BookingRequest missingEnd = new BookingDtos.BookingRequest(
                room.getId(), "Priya", at(9, 0), null, List.of("a"));

        assertThatThrownBy(() -> service.create(missingStart))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("startTime and endTime are required");
        assertThatThrownBy(() -> service.create(missingEnd))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("startTime and endTime are required");
    }

    @Test
    @DisplayName("A null attendees list is rejected rather than throwing a NullPointerException")
    void nullAttendees_is400() {
        Room room = rooms.findByName("Room A").orElseThrow();
        BookingDtos.BookingRequest request = new BookingDtos.BookingRequest(
                room.getId(), "Priya", at(9, 0), at(10, 0), null);

        assertThatThrownBy(() -> service.create(request))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("attendees must contain at least one attendee");
    }

    @Test
    @DisplayName("A past start time is rejected at the service layer too")
    void pastStartTime_is400() {
        Room room = rooms.findByName("Room A").orElseThrow();
        OffsetDateTime start = LocalDate.of(2020, 1, 6).atTime(9, 0).atOffset(ZoneOffset.UTC);
        BookingDtos.BookingRequest request = new BookingDtos.BookingRequest(
                room.getId(), "Priya", start, start.plusHours(1), List.of("a"));

        assertThatThrownBy(() -> service.create(request))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("startTime must not be in the past");
    }

    @Test
    @DisplayName("Equivalent instants in different offsets collide at the service layer")
    void equivalentOffsets_collide() {
        Room room = rooms.findByName("Room A").orElseThrow();
        service.create(new BookingDtos.BookingRequest(
                room.getId(), "Priya", at(9, 0), at(10, 0), List.of("a")));

        // 14:30+05:30 == 09:00Z
        OffsetDateTime sameInstant = OffsetDateTime.of(2026, 11, 2, 14, 30, 0, 0, ZoneOffset.ofHoursMinutes(5, 30));
        BookingDtos.BookingRequest clashing = new BookingDtos.BookingRequest(
                room.getId(), "Arun", sameInstant, sameInstant.plusHours(1), List.of("b"));

        assertThatThrownBy(() -> service.create(clashing)).isInstanceOf(ApiException.Conflict.class);
    }

    @Test
    @DisplayName("Blank attendees are rejected at the service layer")
    void blankAttendees_is400() {
        Room room = rooms.findByName("Room A").orElseThrow();
        BookingDtos.BookingRequest request = new BookingDtos.BookingRequest(
                room.getId(), "Priya", at(9, 0), at(10, 0), Arrays.asList("a", " "));

        assertThatThrownBy(() -> service.create(request))
                .isInstanceOf(ApiException.BadRequest.class)
                .hasMessage("attendees must not contain blank entries");
    }

    private static OffsetDateTime at(int hour, int minute) {
        return MONDAY.atTime(hour, minute).atOffset(ZoneOffset.UTC);
    }
}
