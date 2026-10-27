package com.sdsi.booking.service;

import com.sdsi.booking.web.error.ApiException;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Single source of truth for attendee-list hygiene, shared by the CRUD and recurrence
 * paths so both reject the same inputs with the same message.
 *
 * <p>Identity is compared case-insensitively after trimming, because the same person
 * arriving as {@code "Dev-1"} and {@code " dev-1"} would otherwise be counted twice
 * against room capacity and receive two invitations.
 */
public final class AttendeeRules {

    private AttendeeRules() {
    }

    /**
     * @return trimmed, duplicate-free attendees in the caller's order
     * @throws ApiException.BadRequest when the list is empty, contains blank entries,
     *                                 or repeats an attendee (case-insensitive)
     */
    public static List<String> normalise(List<String> attendees) {
        if (attendees == null || attendees.isEmpty()) {
            throw new ApiException.BadRequest("attendees must contain at least one attendee");
        }

        List<String> cleaned = new ArrayList<>(attendees.size());
        List<String> duplicates = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();

        for (String raw : attendees) {
            if (raw == null || raw.isBlank()) {
                throw new ApiException.BadRequest("attendees must not contain blank entries");
            }
            String trimmed = raw.trim();
            if (!seen.add(trimmed.toLowerCase(Locale.ROOT))) {
                duplicates.add(trimmed);
                continue;
            }
            cleaned.add(trimmed);
        }

        if (!duplicates.isEmpty()) {
            throw new ApiException.BadRequest(
                    "attendees must be unique; duplicated: " + String.join(", ", duplicates));
        }
        return List.copyOf(cleaned);
    }
}
