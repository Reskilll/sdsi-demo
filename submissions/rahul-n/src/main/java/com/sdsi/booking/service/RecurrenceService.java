package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.web.dto.BookingDtos;
import com.sdsi.booking.web.error.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

/**
 * M5 — weekly recurrence as a two-step, dry-run-then-confirm flow.
 *
 * <ol>
 *   <li>{@link #dryRun} validates every weekly occurrence, records why each blocked date
 *       fails, and returns a signed plan token covering only the available slots.</li>
 *   <li>{@link #commit} replays that token, re-validates against live data (so a booking
 *       made in between is still caught), and persists only the slots that survive —
 *       either the whole vetted set or an explicit client-selected subset.</li>
 * </ol>
 */
@Service
public class RecurrenceService {

    public static final int MAX_OCCURRENCES = 52;
    public static final String COMMIT_ENDPOINT = "/api/bookings/recurring/confirm";

    private final RoomRepository rooms;
    private final BookingRepository bookings;
    private final PlanTokenService planTokens;

    public RecurrenceService(RoomRepository rooms, BookingRepository bookings, PlanTokenService planTokens) {
        this.rooms = rooms;
        this.bookings = bookings;
        this.planTokens = planTokens;
    }

    /** Step 1: validate the series, persist nothing. */
    @Transactional(readOnly = true)
    public BookingDtos.RecurrenceDryRunResponse dryRun(BookingDtos.BookingRequest request, int occurrences) {
        if (occurrences < 1 || occurrences > MAX_OCCURRENCES) {
            throw new ApiException.BadRequest("occurrences must be between 1 and " + MAX_OCCURRENCES);
        }
        Room room = rooms.findById(request.roomId())
                .orElseThrow(() -> new ApiException.NotFound("room %d not found".formatted(request.roomId())));
        if (request.startTime() == null || request.endTime() == null) {
            throw new ApiException.BadRequest("startTime and endTime are required");
        }
        if (request.organiser() == null || request.organiser().isBlank()) {
            throw new ApiException.BadRequest("organiser is required");
        }
        OffsetDateTime start = request.startTime().withOffsetSameInstant(ZoneOffset.UTC);
        OffsetDateTime end = request.endTime().withOffsetSameInstant(ZoneOffset.UTC);
        List<String> attendees = AttendeeRules.normalise(request.attendees());
        if (!end.isAfter(start)) {
            throw new ApiException.BadRequest("endTime must be strictly after startTime");
        }
        if (!BusinessHours.isWithinWorkingHours(start, end)) {
            throw new ApiException.BadRequest(
                    "the recurring window must fall inside 09:00-18:00 UTC on a single weekday");
        }
        if (attendees.size() > room.getCapacity()) {
            throw new ApiException.CapacityExceeded(
                    "attendees (%d) exceed %s capacity (%d)"
                            .formatted(attendees.size(), room.getName(), room.getCapacity()));
        }

        List<BookingDtos.OccurrencePlan> plan = new ArrayList<>(occurrences);
        List<OffsetDateTime> availableStarts = new ArrayList<>();
        for (int week = 0; week < occurrences; week++) {
            OffsetDateTime slotStart = start.plusWeeks(week);
            OffsetDateTime slotEnd = end.plusWeeks(week);
            String reason = blockingReason(room, slotStart, slotEnd);
            if (reason == null) {
                plan.add(new BookingDtos.OccurrencePlan(slotStart, slotEnd, true, null));
                availableStarts.add(slotStart);
            } else {
                plan.add(new BookingDtos.OccurrencePlan(slotStart, slotEnd, false, reason));
            }
        }

        int durationMinutes = (int) BusinessHours.minutesBetween(start, end);
        OffsetDateTime expiresAt = planTokens.expiryFromNow();
        String token = availableStarts.isEmpty() ? null : planTokens.issue(new PlanTokenService.PlanPayload(
                room.getId(), request.organiser().trim(), attendees,
                availableStarts, durationMinutes, expiresAt));

        long conflictCount = plan.size() - availableStarts.size();
        return new BookingDtos.RecurrenceDryRunResponse(
                token,
                !availableStarts.isEmpty(),
                conflictCount == 0,
                occurrences,
                availableStarts.size(),
                (int) conflictCount,
                plan,
                COMMIT_ENDPOINT,
                expiresAt);
    }

    /**
     * Step 2: persist the surviving occurrences.
     *
     * <p>{@code selected} semantics: {@code null} commits every vetted slot; an explicit
     * list commits exactly that subset (an empty list commits nothing, which is how a
     * client declines the plan without discarding the token). Slots absent from the signed
     * plan are rejected outright.
     */
    @Transactional
    public BookingDtos.RecurrenceCommitResponse commit(String planToken, List<BookingDtos.OccurrencePlan> selected) {
        PlanTokenService.PlanPayload payload = planTokens.verify(planToken);
        Room room = rooms.findByIdForUpdate(payload.roomId())
                .orElseThrow(() -> new ApiException.NotFound("room %d not found".formatted(payload.roomId())));

        List<OffsetDateTime> toCommit = resolveSelection(payload, selected);

        List<BookingDtos.BookingResponse> saved = new ArrayList<>();
        List<BookingDtos.OccurrencePlan> skipped = new ArrayList<>();
        for (OffsetDateTime slotStart : toCommit) {
            OffsetDateTime slotEnd = slotStart.plusMinutes(payload.durationMinutes());
            String reason = blockingReason(room, slotStart, slotEnd);
            if (reason != null) {
                skipped.add(new BookingDtos.OccurrencePlan(slotStart, slotEnd, false, reason));
                continue;
            }
            Booking booking = bookings.save(
                    new Booking(room, payload.organiser(), slotStart, slotEnd, payload.attendees()));
            saved.add(BookingDtos.BookingResponse.from(booking));
        }
        return new BookingDtos.RecurrenceCommitResponse(saved.size(), skipped.size(), saved, skipped);
    }

    // ---------------------------------------------------------------- internals

    private List<OffsetDateTime> resolveSelection(PlanTokenService.PlanPayload payload,
                                                  List<BookingDtos.OccurrencePlan> selected) {
        if (selected == null) {
            return payload.slots();
        }
        List<OffsetDateTime> resolved = new ArrayList<>();
        for (BookingDtos.OccurrencePlan candidate : selected) {
            OffsetDateTime start = candidate.startTime() == null
                    ? null
                    : candidate.startTime().withOffsetSameInstant(ZoneOffset.UTC);
            // Membership is checked against the signed plan, so a client cannot smuggle in
            // a slot the dry-run never vetted.
            if (start == null || !payload.slots().contains(start)) {
                throw new ApiException.BadRequest(
                        "occurrence %s is not part of this plan".formatted(candidate.startTime()));
            }
            if (!resolved.contains(start)) {
                resolved.add(start);
            }
        }
        return resolved;
    }

    /** Null when the slot is bookable; otherwise a human-readable blocker. */
    private String blockingReason(Room room, OffsetDateTime start, OffsetDateTime end) {
        if (!BusinessHours.isWithinWorkingHours(start, end)) {
            return "outside 09:00-18:00 UTC on a weekday";
        }
        List<Booking> conflicts = bookings.findOverlapping(room.getId(), start, end);
        if (!conflicts.isEmpty()) {
            Booking first = conflicts.get(0);
            return "conflicts with %s-%s (%s)".formatted(
                    first.getStartTime(), first.getEndTime(), first.getOrganiser());
        }
        return null;
    }
}
