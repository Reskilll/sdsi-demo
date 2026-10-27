package com.sdsi.booking.service;

import com.sdsi.booking.config.AppProperties;
import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.BookingStatus;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repo.BookingRepository;
import com.sdsi.booking.repo.RoomRepository;
import com.sdsi.booking.web.dto.BusyInterval;
import com.sdsi.booking.web.dto.FreeInterval;
import com.sdsi.booking.web.dto.RoomAvailabilityResponse;
import com.sdsi.booking.web.dto.SlotSearchResponse;
import com.sdsi.booking.web.dto.SlotView;
import com.sdsi.booking.web.error.NotFoundException;
import com.sdsi.booking.web.error.RuleViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class SlotService {

    private static final int MAX_ALTERNATIVES = 5;

    private final RoomRepository roomRepository;
    private final BookingRepository bookingRepository;
    private final BookingMapper mapper;
    private final OfficeHours officeHours;
    private final Clock clock;
    private final int gridMinutes;

    public SlotService(RoomRepository roomRepository, BookingRepository bookingRepository,
                       BookingMapper mapper, OfficeHours officeHours, Clock clock,
                       AppProperties properties) {
        this.roomRepository = roomRepository;
        this.bookingRepository = bookingRepository;
        this.mapper = mapper;
        this.officeHours = officeHours;
        this.clock = clock;
        this.gridMinutes = properties.office().slotGridMinutes();
    }

    /**
     * Finds the earliest free room/time on {@code date} for the requested
     * duration and headcount. Candidate start times lie on the configured grid
     * (15 minutes by default) and must finish by the office closing time.
     */
    @Transactional(readOnly = true)
    public SlotSearchResponse findSlot(LocalDate date, int durationMinutes, int attendees,
                                       List<String> amenities, String roomId) {
        validateSearch(date, durationMinutes, attendees);

        Room requestedRoom = null;
        if (roomId != null && !roomId.isBlank()) {
            requestedRoom = roomRepository.findByIdAndActiveTrue(roomId.trim())
                    .orElseThrow(() -> new NotFoundException("Room", roomId));
        }

        List<String> wantedAmenities = amenities == null ? List.of() : amenities.stream()
                .filter(Objects::nonNull)
                .map(a -> a.trim().toLowerCase(Locale.ROOT))
                .filter(a -> !a.isEmpty())
                .distinct()
                .toList();

        List<Room> candidates = (requestedRoom != null
                ? List.of(requestedRoom)
                : roomRepository.findByActiveTrueOrderByCapacityAscNameAsc())
                .stream()
                .filter(room -> room.getCapacity() >= attendees)
                .filter(room -> amenitySet(room).containsAll(wantedAmenities))
                .toList();

        if (candidates.isEmpty()) {
            return noSlot(date, durationMinutes, attendees,
                    "No active room satisfies the attendee count and requested amenities.");
        }

        LocalDateTime open = officeHours.openOn(date);
        LocalDateTime close = officeHours.closeOn(date);
        LocalDateTime earliest = open;
        boolean today = date.equals(LocalDate.now(clock));
        if (today) {
            earliest = latest(open, ceilToGrid(roundUpToMinute(LocalDateTime.now(clock))));
        }
        if (!earliest.isBefore(close)) {
            return noSlot(date, durationMinutes, attendees,
                    today ? "Today's booking window has already closed." : "No slot available.");
        }

        List<Booking> busy = bookingRepository.findBusyForRooms(
                candidates.stream().map(Room::getId).toList(), open, close, BookingStatus.CONFIRMED);
        Map<String, List<Booking>> busyByRoom = busy.stream()
                .collect(Collectors.groupingBy(b -> b.getRoom().getId(), LinkedHashMap::new, Collectors.toList()));

        List<SlotView> roomEarliest = new ArrayList<>();
        for (Room room : candidates) {
            LocalDateTime candidate = earliestFreeStart(
                    open, close, busyByRoom.getOrDefault(room.getId(), List.of()), earliest, durationMinutes);
            if (candidate != null) {
                roomEarliest.add(new SlotView(candidate, candidate.plusMinutes(durationMinutes), mapper.toRoom(room)));
            }
        }

        roomEarliest.sort(Comparator
                .comparing(SlotView::start)
                .thenComparing(slot -> slot.room().capacity())
                .thenComparing(slot -> slot.room().name()));

        if (roomEarliest.isEmpty()) {
            return noSlot(date, durationMinutes, attendees,
                    "No free " + durationMinutes + "-minute slot remains for " + attendees
                            + " attendees on " + date + ".");
        }

        SlotView best = roomEarliest.get(0);
        List<SlotView> alternatives = roomEarliest.stream()
                .skip(1)
                .limit(MAX_ALTERNATIVES)
                .toList();
        return new SlotSearchResponse(date, durationMinutes, attendees, best, alternatives, null);
    }

    @Transactional(readOnly = true)
    public RoomAvailabilityResponse availability(String roomId, LocalDate date) {
        Room room = roomRepository.findByIdAndActiveTrue(roomId)
                .orElseThrow(() -> new NotFoundException("Room", roomId));
        LocalDateTime open = officeHours.openOn(date);
        LocalDateTime close = officeHours.closeOn(date);
        List<Booking> busy = bookingRepository.findBusyForRooms(
                List.of(room.getId()), open, close, BookingStatus.CONFIRMED);

        List<TimeRange> free = freeWindows(open, close, busy);
        List<BusyInterval> busyIntervals = busy.stream()
                .filter(b -> b.getStart().isBefore(close) && b.getEnd().isAfter(open))
                .map(b -> new BusyInterval(
                        latest(b.getStart(), open), earliest(b.getEnd(), close),
                        b.getId(), b.getTitle(), b.getOrganiser()))
                .toList();
        List<FreeInterval> freeIntervals = free.stream()
                .map(window -> new FreeInterval(window.start(), window.end(),
                        Duration.between(window.start(), window.end()).toMinutes()))
                .toList();
        return new RoomAvailabilityResponse(mapper.toRoom(room), date, busyIntervals, freeIntervals);
    }

    private void validateSearch(LocalDate date, int durationMinutes, int attendees) {
        if (durationMinutes < officeHours.getMinDurationMinutes()
                || durationMinutes > officeHours.getMaxDurationMinutes()) {
            throw new RuleViolationException("INVALID_DURATION",
                    "durationMinutes must be between " + officeHours.getMinDurationMinutes()
                            + " and " + officeHours.getMaxDurationMinutes() + ".");
        }
        if (attendees < 1) {
            throw new RuleViolationException("INVALID_ATTENDEES", "attendees must be at least 1.");
        }
        if (date.isBefore(LocalDate.now(clock))) {
            throw new RuleViolationException("DATE_IN_PAST",
                    "Cannot search for availability on a past date.");
        }
    }

    private LocalDateTime earliestFreeStart(LocalDateTime open, LocalDateTime close, List<Booking> busy,
                                            LocalDateTime notBefore, int durationMinutes) {
        for (TimeRange window : freeWindows(open, close, busy)) {
            LocalDateTime candidate = ceilToGrid(latest(window.start(), notBefore));
            if (!candidate.plusMinutes(durationMinutes).isAfter(window.end())) {
                return candidate;
            }
        }
        return null;
    }

    /**
     * Returns the free gaps inside [open, close) after subtracting and merging
     * the busy intervals. Half-open intervals keep back-to-back bookings apart.
     */
    private static List<TimeRange> freeWindows(LocalDateTime open, LocalDateTime close,
                                               List<Booking> busy) {
        return FreeWindows.compute(open, close, busy.stream()
                .map(booking -> new TimeRange(booking.getStart(), booking.getEnd()))
                .toList());
    }

    private LocalDateTime ceilToGrid(LocalDateTime time) {
        LocalDateTime anchor = officeHours.openOn(time.toLocalDate());
        if (time.isBefore(anchor)) {
            return anchor;
        }
        long minutes = Duration.between(anchor, time).toMinutes();
        long remainder = minutes % gridMinutes;
        return remainder == 0 ? time : time.plusMinutes(gridMinutes - remainder);
    }

    private static LocalDateTime roundUpToMinute(LocalDateTime time) {
        LocalDateTime truncated = time.truncatedTo(ChronoUnit.MINUTES);
        return truncated.equals(time) ? truncated : truncated.plusMinutes(1);
    }

    private static Set<String> amenitySet(Room room) {
        return room.getAmenities().stream()
                .map(a -> a.toLowerCase(Locale.ROOT))
                .collect(Collectors.toSet());
    }

    private static LocalDateTime latest(LocalDateTime a, LocalDateTime b) {
        return FreeWindows.latest(a, b);
    }

    private static LocalDateTime earliest(LocalDateTime a, LocalDateTime b) {
        return FreeWindows.earliest(a, b);
    }

    private static SlotSearchResponse noSlot(LocalDate date, int durationMinutes, int attendees, String message) {
        return new SlotSearchResponse(date, durationMinutes, attendees, null, List.of(), message);
    }
}
