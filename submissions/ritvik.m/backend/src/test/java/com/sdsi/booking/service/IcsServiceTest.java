package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class IcsServiceTest {

    private final IcsService service = new IcsService();

    private Booking booking() {
        Room room = new Room("atlas", "Atlas", 4, 1, "North Wing", Set.of("tv"));
        return new Booking(UUID.randomUUID(), room, null, null, "Ritvik", "ritvik@example.com",
                "Sync, planning; Q4", "Quarterly planning",
                LocalDateTime.of(2026, 11, 2, 10, 0),
                LocalDateTime.of(2026, 11, 2, 11, 0),
                2, Set.of("ada@example.com", "grace@example.com"));
    }

    @Test
    void rendersCalendarWithFloatingLocalTimes() {
        String ics = service.render(booking());

        assertThat(ics).startsWith("BEGIN:VCALENDAR\r\n");
        assertThat(ics).contains("DTSTART:20261102T100000\r\n");
        assertThat(ics).contains("DTEND:20261102T110000\r\n");
        assertThat(ics).contains("SUMMARY:Sync\\, planning\\; Q4\r\n");
        assertThat(ics).contains("LOCATION:Atlas\\, Floor 1\\, North Wing\r\n");
        assertThat(ics).contains("STATUS:CONFIRMED\r\n");
        assertThat(ics).endsWith("END:VCALENDAR\r\n");
    }

    @Test
    void cancelledBookingIsMarkedCancelled() {
        Booking booking = booking();
        booking.cancel();
        assertThat(service.render(booking)).contains("STATUS:CANCELLED\r\n");
    }

    @Test
    void userTextCannotInjectCalendarLines() {
        Room room = new Room("atlas", "Atlas", 4, 1, "North", Set.of());
        Booking booking = new Booking(UUID.randomUUID(), room, null, null, "Ritvik", null,
                "Sync\nATTENDEE:mailto:evil@example.com", null,
                LocalDateTime.of(2026, 11, 2, 10, 0),
                LocalDateTime.of(2026, 11, 2, 11, 0),
                1, Set.of());
        String ics = service.render(booking);

        assertThat(ics).contains("SUMMARY:Sync\\nATTENDEE:mailto:evil@example.com\r\n");
        assertThat(ics).doesNotContain("\r\nATTENDEE:");
    }

    @Test
    void longLinesAreFoldedToTheIcsLimit() {
        Room room = new Room("atlas", "Atlas", 4, null, null, Set.of());
        Booking booking = new Booking(UUID.randomUUID(), room, null, null, "Ritvik", null,
                "A".repeat(120), "B".repeat(300),
                LocalDateTime.of(2026, 11, 2, 10, 0),
                LocalDateTime.of(2026, 11, 2, 11, 0),
                1, Set.of());
        String ics = service.render(booking);

        for (String line : ics.split("\r\n")) {
            assertThat(line.length()).isLessThanOrEqualTo(75);
        }
    }

    @Test
    void escapesSpecialCharacters() {
        assertThat(IcsService.escape("a,b;c\\d\r\ne"))
                .isEqualTo("a\\,b\\;c\\\\d\\ne");
        assertThat(IcsService.escape(null)).isEmpty();
    }
}
