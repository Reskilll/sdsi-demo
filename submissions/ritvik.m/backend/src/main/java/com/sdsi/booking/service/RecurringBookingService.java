package com.sdsi.booking.service;

import com.sdsi.booking.config.AppProperties;
import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.BookingSeries;
import com.sdsi.booking.domain.BookingStatus;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repo.BookingRepository;
import com.sdsi.booking.repo.BookingSeriesRepository;
import com.sdsi.booking.repo.RoomRepository;
import com.sdsi.booking.web.dto.BookingResponse;
import com.sdsi.booking.web.dto.CancelSeriesResponse;
import com.sdsi.booking.web.dto.ConflictView;
import com.sdsi.booking.web.dto.OccurrenceStatus;
import com.sdsi.booking.web.dto.OccurrenceView;
import com.sdsi.booking.web.dto.PageResponse;
import com.sdsi.booking.web.dto.RecurringBookingRequest;
import com.sdsi.booking.web.dto.RecurringCreateResponse;
import com.sdsi.booking.web.dto.RecurringPreviewResponse;
import com.sdsi.booking.web.dto.SeriesResponse;
import com.sdsi.booking.web.dto.SeriesSummaryResponse;
import com.sdsi.booking.web.error.NotFoundException;
import com.sdsi.booking.web.error.RecurringConflictException;
import com.sdsi.booking.web.error.RuleViolationException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

@Service
public class RecurringBookingService {

    private final BookingRepository bookingRepository;
    private final BookingSeriesRepository seriesRepository;
    private final RoomRepository roomRepository;
    private final BookingMapper mapper;
    private final OfficeHours officeHours;
    private final Clock clock;
    private final int maxPageSize;

    public RecurringBookingService(BookingRepository bookingRepository,
                                   BookingSeriesRepository seriesRepository,
                                   RoomRepository roomRepository,
                                   BookingMapper mapper,
                                   OfficeHours officeHours,
                                   Clock clock,
                                   AppProperties properties) {
        this.bookingRepository = bookingRepository;
        this.seriesRepository = seriesRepository;
        this.roomRepository = roomRepository;
        this.mapper = mapper;
        this.officeHours = officeHours;
        this.clock = clock;
        this.maxPageSize = properties.office().maxPageSize();
    }

    /**
     * Calculates conflicts for the whole series first and only then writes.
     * By default the operation is atomic: any conflict means nothing is
     * created and every conflicting occurrence is reported. With
     * {@code skipConflicts=true} the free occurrences are still created.
     */
    @Transactional
    public RecurringCreateResponse create(RecurringBookingRequest request) {
        Room room = roomRepository.findActiveForUpdate(request.roomId())
                .orElseThrow(() -> new NotFoundException("Room", request.roomId()));
        Plan plan = plan(room, request);

        int conflictCount = (int) plan.occurrences().stream()
                .filter(o -> o.status() == OccurrenceStatus.CONFLICT)
                .count();

        if (conflictCount > 0 && (!request.skipConflicts() || conflictCount == plan.occurrences().size())) {
            throw new RecurringConflictException(plan.occurrences(), conflictCount, plan.occurrences().size());
        }

        BookingSeries series = new BookingSeries(
                UUID.randomUUID(),
                room,
                clean(request.organiser()),
                cleanEmail(request.organiserEmail()),
                clean(request.title()),
                clean(request.description()),
                request.startTime(),
                request.endTime(),
                request.startsOn(),
                request.weeks(),
                new TreeSet<>(plan.days()),
                plan.attendees().count(),
                plan.attendees().names());
        seriesRepository.saveAndFlush(series);

        List<Booking> created = new ArrayList<>();
        for (int index = 0; index < plan.occurrences().size(); index++) {
            OccurrenceView occurrence = plan.occurrences().get(index);
            if (occurrence.status() != OccurrenceStatus.FREE) {
                continue;
            }
            Booking booking = new Booking(
                    UUID.randomUUID(),
                    room,
                    series,
                    index + 1,
                    series.getOrganiser(),
                    series.getOrganiserEmail(),
                    series.getTitle(),
                    series.getDescription(),
                    occurrence.start(),
                    occurrence.end(),
                    series.getAttendeeCount(),
                    series.getAttendees());
            created.add(booking);
        }
        bookingRepository.saveAll(created);
        bookingRepository.flush();

        List<OccurrenceView> skipped = plan.occurrences().stream()
                .filter(o -> o.status() == OccurrenceStatus.CONFLICT)
                .toList();
        String message = skipped.isEmpty()
                ? "Created " + created.size() + " occurrence(s)."
                : "Created " + created.size() + " of " + plan.occurrences().size()
                        + " occurrence(s); " + skipped.size() + " skipped due to conflicts.";

        return new RecurringCreateResponse(
                series.getId(),
                mapper.toSeriesSummary(series),
                created.stream().map(mapper::toBooking).toList(),
                skipped,
                message);
    }

    @Transactional(readOnly = true)
    public RecurringPreviewResponse preview(RecurringBookingRequest request) {
        Room room = roomRepository.findByIdAndActiveTrue(request.roomId())
                .orElseThrow(() -> new NotFoundException("Room", request.roomId()));
        Plan plan = plan(room, request);
        int conflictCount = (int) plan.occurrences().stream()
                .filter(o -> o.status() == OccurrenceStatus.CONFLICT)
                .count();
        return new RecurringPreviewResponse(
                request.startsOn(),
                request.weeks(),
                List.copyOf(plan.days()),
                plan.occurrences().size(),
                conflictCount,
                plan.occurrences());
    }

    @Transactional(readOnly = true)
    public SeriesResponse getSeries(UUID id) {
        BookingSeries series = seriesRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Series", id));
        return mapper.toSeries(series, bookingRepository.findBySeriesIdOrderByStart(id));
    }

    @Transactional(readOnly = true)
    public PageResponse<SeriesSummaryResponse> listSeries(int page, int size) {
        if (page < 0) {
            throw new RuleViolationException("INVALID_PAGE", "page must be zero or greater.");
        }
        if (size < 1 || size > maxPageSize) {
            throw new RuleViolationException("INVALID_PAGE_SIZE",
                    "size must be between 1 and " + maxPageSize + ".");
        }
        Page<BookingSeries> result = seriesRepository.findAll(
                PageRequest.of(page, size, Sort.by(Sort.Order.desc("createdAt"))));
        return PageResponse.from(result, mapper::toSeriesSummary);
    }

    /**
     * Cancels confirmed occurrences of the series that start at or after
     * {@code from} (defaults to now). Returns how many were cancelled.
     */
    @Transactional
    public CancelSeriesResponse cancelSeries(UUID id, LocalDateTime from) {
        BookingSeries series = seriesRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Series", id));
        LocalDateTime effectiveFrom = from != null ? from : LocalDateTime.now(clock);
        List<Booking> occurrences = bookingRepository.findSeriesOccurrencesFrom(
                series.getId(), BookingStatus.CONFIRMED, effectiveFrom);
        occurrences.forEach(Booking::cancel);
        bookingRepository.flush();
        return new CancelSeriesResponse(id, occurrences.size());
    }

    private Plan plan(Room room, RecurringBookingRequest request) {
        officeHours.validateWindow(request.startsOn().atTime(request.startTime()),
                request.startsOn().atTime(request.endTime()));

        Attendees.AttendeeData attendeeData = Attendees.resolve(request.attendeeCount(), request.attendees());
        Attendees.checkCapacity(attendeeData, room.getName(), room.getCapacity());

        Set<DayOfWeek> days = request.daysOfWeek() == null || request.daysOfWeek().isEmpty()
                ? new TreeSet<>(Set.of(request.startsOn().getDayOfWeek()))
                : new TreeSet<>(request.daysOfWeek());
        List<DayOfWeek> orderedDays = List.copyOf(days);

        List<LocalDate> dates = RecurrenceGenerator.occurrenceDates(request.startsOn(), request.weeks(), orderedDays);
        LocalDateTime firstStart = dates.get(0).atTime(request.startTime());
        LocalDateTime lastEnd = dates.get(dates.size() - 1).atTime(request.endTime());

        // A single range query for the whole series; conflicts are then matched
        // per occurrence in memory instead of issuing N queries.
        List<Booking> existing = bookingRepository.findBusyForRooms(
                List.of(room.getId()), firstStart, lastEnd, BookingStatus.CONFIRMED);

        List<OccurrenceView> occurrences = new ArrayList<>(dates.size());
        for (LocalDate date : dates) {
            LocalDateTime start = date.atTime(request.startTime());
            LocalDateTime end = date.atTime(request.endTime());
            List<ConflictView> conflicts = existing.stream()
                    .filter(booking -> overlaps(start, end, booking.getStart(), booking.getEnd()))
                    .map(mapper::toConflict)
                    .toList();
            occurrences.add(new OccurrenceView(start, end,
                    conflicts.isEmpty() ? OccurrenceStatus.FREE : OccurrenceStatus.CONFLICT,
                    conflicts));
        }
        return new Plan(orderedDays, attendeeData, List.copyOf(occurrences));
    }

    private static boolean overlaps(LocalDateTime start, LocalDateTime end,
                                    LocalDateTime otherStart, LocalDateTime otherEnd) {
        return otherStart.isBefore(end) && otherEnd.isAfter(start);
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static String cleanEmail(String value) {
        String cleaned = clean(value);
        return cleaned == null ? null : cleaned.toLowerCase(java.util.Locale.ROOT);
    }

    private record Plan(List<DayOfWeek> days, Attendees.AttendeeData attendees,
                        List<OccurrenceView> occurrences) {
    }
}
