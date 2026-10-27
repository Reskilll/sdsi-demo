package com.sdsi.booking.web.dto;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.FutureOrPresent;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.OffsetDateTime;
import java.util.List;

/** Request/response payloads for the booking REST layer. */
public final class BookingDtos {

    private BookingDtos() {
    }

    /**
     * Inbound booking. {@code @FutureOrPresent} on {@code startTime} and the class-level
     * window assertion are enforced before the service is ever reached; the service
     * re-checks both so programmatic callers cannot skip the guards.
     */
    public record BookingRequest(
            @NotNull(message = "roomId is required")
            Long roomId,

            @NotBlank(message = "organiser is required")
            @Size(max = 128, message = "organiser must not exceed 128 characters")
            String organiser,

            @NotNull(message = "startTime is required")
            @FutureOrPresent(message = "startTime must be today or in the future")
            OffsetDateTime startTime,

            @NotNull(message = "endTime is required")
            OffsetDateTime endTime,

            @NotEmpty(message = "attendees must contain at least one attendee")
            @Size(max = 100, message = "attendees must not exceed 100 entries")
            List<@NotBlank(message = "attendee must not be blank")
                 @Size(max = 128, message = "attendee must not exceed 128 characters") String> attendees
    ) {

        @AssertTrue(message = "endTime must be strictly after startTime")
        public boolean isWindowValid() {
            return startTime == null || endTime == null || endTime.isAfter(startTime);
        }
    }

    public record BookingResponse(
            Long id,
            Long roomId,
            String roomName,
            String organiser,
            OffsetDateTime startTime,
            OffsetDateTime endTime,
            List<String> attendees
    ) {
        public static BookingResponse from(Booking b) {
            return new BookingResponse(
                    b.getId(),
                    b.getRoomId(),
                    b.getRoom().getName(),
                    b.getOrganiser(),
                    b.getStartTime(),
                    b.getEndTime(),
                    List.copyOf(b.getAttendees()));
        }
    }

    public record RoomResponse(Long id, String name, int capacity) {
        public static RoomResponse from(Room r) {
            return new RoomResponse(r.getId(), r.getName(), r.getCapacity());
        }
    }

    public record SlotSuggestion(
            Long roomId,
            String roomName,
            int roomCapacity,
            OffsetDateTime startTime,
            OffsetDateTime endTime
    ) {
    }

    /**
     * One planned weekly occurrence. {@code available=false} carries the reason the slot
     * cannot be committed, so the dry-run response is self-explaining.
     */
    public record OccurrencePlan(
            @NotNull OffsetDateTime startTime,
            @NotNull OffsetDateTime endTime,
            boolean available,
            String reason
    ) {
    }

    public record RecurrenceDryRunResponse(
            String planToken,
            boolean executable,
            boolean allAvailable,
            int requestedOccurrences,
            int availableCount,
            int conflictCount,
            List<OccurrencePlan> occurrences,
            String commitEndpoint,
            OffsetDateTime expiresAt
    ) {
    }

    /**
     * Step-2 payload. {@code occurrences} is optional: {@code null} commits every vetted
     * slot, an explicit list commits exactly that subset (empty list commits nothing).
     */
    public record RecurrenceCommitRequest(
            @NotBlank(message = "planToken is required")
            String planToken,

            @Valid
            List<@Valid OccurrencePlan> occurrences
    ) {
    }

    public record RecurrenceCommitResponse(
            int savedCount,
            int skippedCount,
            List<BookingResponse> savedBookings,
            List<OccurrencePlan> skipped
    ) {
    }

    public record RoomUtilization(
            Long roomId,
            String roomName,
            int capacity,
            long bookedMinutes,
            long availableMinutes,
            double utilizationPercent
    ) {
    }

    public record UtilizationResponse(
            OffsetDateTime from,
            OffsetDateTime to,
            int workingHoursPerDay,
            List<RoomUtilization> rooms
    ) {
    }

    public record ApiError(
            OffsetDateTime timestamp,
            int status,
            String error,
            String message,
            String path,
            List<String> details
    ) {
        public static ApiError of(int status, String error, String message, String path, List<String> details) {
            return new ApiError(OffsetDateTime.now(), status, error, message, path, details);
        }
    }
}
