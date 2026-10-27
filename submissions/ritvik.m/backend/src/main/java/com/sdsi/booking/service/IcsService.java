package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/**
 * Renders a single booking as an RFC 5545 calendar file. Times are emitted as
 * floating local times because the API models office wall-clock time.
 */
@Component
public class IcsService {

    private static final DateTimeFormatter EVENT_TIME = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss");
    private static final DateTimeFormatter STAMP =
            DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC);

    public String render(Booking booking) {
        StringBuilder ics = new StringBuilder(512);
        appendLine(ics, "BEGIN:VCALENDAR");
        appendLine(ics, "VERSION:2.0");
        appendLine(ics, "PRODID:-//SDSI//Meeting Room Booking//EN");
        appendLine(ics, "CALSCALE:GREGORIAN");
        appendLine(ics, "BEGIN:VEVENT");
        appendLine(ics, "UID:" + booking.getId() + "@room-booking");
        appendLine(ics, "DTSTAMP:" + STAMP.format(Instant.now()));
        appendLine(ics, "DTSTART:" + EVENT_TIME.format(booking.getStart()));
        appendLine(ics, "DTEND:" + EVENT_TIME.format(booking.getEnd()));
        appendLine(ics, "SUMMARY:" + escape(booking.getTitle()));
        appendLine(ics, "LOCATION:" + escape(location(booking)));
        appendLine(ics, "DESCRIPTION:" + escape(description(booking)));
        if (booking.getOrganiserEmail() != null && !booking.getOrganiserEmail().isBlank()) {
            appendLine(ics, "ORGANIZER;CN=" + escape(booking.getOrganiser())
                    + ":mailto:" + escape(booking.getOrganiserEmail()));
        }
        appendLine(ics, "STATUS:" + (booking.getStatus().name().equals("CANCELLED") ? "CANCELLED" : "CONFIRMED"));
        appendLine(ics, "END:VEVENT");
        appendLine(ics, "END:VCALENDAR");
        return ics.toString();
    }

    private static String location(Booking booking) {
        StringBuilder location = new StringBuilder(booking.getRoom().getName());
        if (booking.getRoom().getFloor() != null) {
            location.append(", Floor ").append(booking.getRoom().getFloor());
        }
        if (booking.getRoom().getLocation() != null && !booking.getRoom().getLocation().isBlank()) {
            location.append(", ").append(booking.getRoom().getLocation());
        }
        return location.toString();
    }

    private static String description(Booking booking) {
        StringBuilder description = new StringBuilder();
        description.append("Organiser: ").append(booking.getOrganiser());
        description.append("\nAttendees: ").append(booking.getAttendeeCount());
        if (booking.getDescription() != null && !booking.getDescription().isBlank()) {
            description.append("\n\n").append(booking.getDescription());
        }
        return description.toString();
    }

    /**
     * Escapes special characters so user supplied text cannot inject extra
     * calendar properties or lines.
     */
    static String escape(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("\\", "\\\\")
                .replace("\r\n", "\\n")
                .replace("\n", "\\n")
                .replace("\r", "\\n")
                .replace(";", "\\;")
                .replace(",", "\\,");
    }

    private static void appendLine(StringBuilder target, String line) {
        String remaining = line;
        while (remaining.length() > 73) {
            target.append(remaining, 0, 73).append("\r\n ");
            remaining = remaining.substring(73);
        }
        target.append(remaining).append("\r\n");
    }
}
