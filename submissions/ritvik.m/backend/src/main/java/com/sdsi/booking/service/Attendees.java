package com.sdsi.booking.service;

import com.sdsi.booking.web.error.RuleViolationException;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Normalises the optional attendee list / attendee count pair.
 *
 * <p>The API accepts either, or both. Deduplicating and requiring the two
 * representations to agree avoids the classic "capacity check passed because
 * the count field was empty" bug.</p>
 */
public final class Attendees {

    private Attendees() {
    }

    public record AttendeeData(int count, Set<String> names) {
    }

    public static AttendeeData resolve(Integer attendeeCount, List<String> attendees) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        if (attendees != null) {
            attendees.stream()
                    .filter(Objects::nonNull)
                    .map(String::trim)
                    .filter(name -> !name.isEmpty())
                    .forEach(names::add);
        }

        if (attendeeCount == null && names.isEmpty()) {
            throw new RuleViolationException("ATTENDEES_REQUIRED",
                    "Provide attendeeCount or at least one attendee.");
        }
        if (attendeeCount != null && !names.isEmpty() && attendeeCount != names.size()) {
            throw new RuleViolationException("ATTENDEE_COUNT_MISMATCH",
                    "attendeeCount (" + attendeeCount + ") does not match the number of attendees ("
                            + names.size() + ").");
        }
        int effective = attendeeCount != null ? attendeeCount : names.size();
        if (effective < 1) {
            throw new RuleViolationException("ATTENDEES_REQUIRED",
                    "At least one attendee is required.");
        }
        return new AttendeeData(effective, names);
    }

    public static void checkCapacity(AttendeeData data, String roomName, int capacity) {
        if (data.count() > capacity) {
            throw new RuleViolationException("CAPACITY_EXCEEDED",
                    "Room '" + roomName + "' seats " + capacity + " but " + data.count()
                            + " attendees were requested.");
        }
    }
}
