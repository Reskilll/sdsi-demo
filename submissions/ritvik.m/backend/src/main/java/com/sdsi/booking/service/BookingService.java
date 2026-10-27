package com.sdsi.booking.service;

import com.sdsi.booking.config.AppProperties;
import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.BookingStatus;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repo.BookingRepository;
import com.sdsi.booking.repo.RoomRepository;
import com.sdsi.booking.web.dto.BookingCreateRequest;
import com.sdsi.booking.web.dto.BookingResponse;
import com.sdsi.booking.web.dto.BookingUpdateRequest;
import com.sdsi.booking.web.dto.ConflictView;
import com.sdsi.booking.web.dto.PageResponse;
import com.sdsi.booking.web.error.BookingConflictException;
import com.sdsi.booking.web.error.NotFoundException;
import com.sdsi.booking.web.error.RuleViolationException;
import com.sdsi.booking.web.error.StaleVersionException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@Service
public class BookingService {

    private static final int MAX_ATTENDEES = 50;

    private final BookingRepository bookingRepository;
    private final RoomRepository roomRepository;
    private final BookingMapper mapper;
    private final OfficeHours officeHours;
    private final IcsService icsService;
    private final int maxPageSize;

    public BookingService(BookingRepository bookingRepository, RoomRepository roomRepository,
                          BookingMapper mapper, OfficeHours officeHours, IcsService icsService,
                          AppProperties properties) {
        this.bookingRepository = bookingRepository;
        this.roomRepository = roomRepository;
        this.mapper = mapper;
        this.officeHours = officeHours;
        this.icsService = icsService;
        this.maxPageSize = properties.office().maxPageSize();
    }

    @Transactional
    public BookingResponse create(BookingCreateRequest request) {
        Room room = lockRoom(request.roomId());
        Attendees.AttendeeData attendeeData = validateBusinessRules(room, request.attendeeCount(),
                request.attendees(), request.start(), request.end());

        assertNoOverlap(room.getId(), request.start(), request.end(), null);

        Booking booking = new Booking(
                UUID.randomUUID(),
                room,
                null,
                null,
                clean(request.organiser()),
                cleanEmail(request.organiserEmail()),
                clean(request.title()),
                clean(request.description()),
                request.start(),
                request.end(),
                attendeeData.count(),
                attendeeData.names());
        Booking saved = bookingRepository.saveAndFlush(booking);
        return mapper.toBooking(saved);
    }

    @Transactional
    public BookingResponse update(UUID id, BookingUpdateRequest request) {
        Booking booking = requireBooking(id);
        if (booking.getStatus() == BookingStatus.CANCELLED) {
            throw new RuleViolationException("BOOKING_CANCELLED",
                    "A cancelled booking cannot be modified. Create a new booking instead.");
        }
        if (request.version() != null && request.version() != booking.getVersion()) {
            throw new StaleVersionException(request.version(), booking.getVersion());
        }

        Room room = lockRoom(request.roomId());
        Attendees.AttendeeData attendeeData = validateBusinessRules(room, request.attendeeCount(),
                request.attendees(), request.start(), request.end());

        assertNoOverlap(room.getId(), request.start(), request.end(), booking.getId());

        booking.apply(
                clean(request.organiser()),
                cleanEmail(request.organiserEmail()),
                clean(request.title()),
                clean(request.description()),
                room,
                request.start(),
                request.end(),
                attendeeData.count(),
                attendeeData.names());
        Booking saved = bookingRepository.saveAndFlush(booking);
        return mapper.toBooking(saved);
    }

    @Transactional(readOnly = true)
    public BookingResponse get(UUID id) {
        return mapper.toBooking(requireBooking(id));
    }

    @Transactional(readOnly = true)
    public PageResponse<BookingResponse> search(BookingQuery query) {
        validatePaging(query.page(), query.size());
        if (query.date() != null && (query.from() != null || query.to() != null)) {
            throw new RuleViolationException("INVALID_FILTER",
                    "Use either 'date' or 'from'/'to', not both.");
        }
        if (query.from() != null && query.to() != null && !query.to().isAfter(query.from())) {
            throw new RuleViolationException("INVALID_FILTER", "'to' must be after 'from'.");
        }

        LocalDateTime from = query.from();
        LocalDateTime to = query.to();
        if (query.date() != null) {
            from = query.date().atStartOfDay();
            to = from.plusDays(1);
        }

        Specification<Booking> spec = (root, cq, cb) -> cb.conjunction();
        if (query.roomId() != null && !query.roomId().isBlank()) {
            String roomId = query.roomId().trim();
            spec = spec.and((root, cq, cb) -> cb.equal(root.get("room").get("id"), roomId));
        }
        if (query.organiser() != null && !query.organiser().isBlank()) {
            String organiser = query.organiser().trim().toLowerCase(Locale.ROOT);
            spec = spec.and((root, cq, cb) -> cb.equal(cb.lower(root.get("organiser")), organiser));
        }
        if (query.status() != null) {
            BookingStatus status = query.status();
            spec = spec.and((root, cq, cb) -> cb.equal(root.get("status"), status));
        }
        if (query.seriesId() != null) {
            UUID seriesId = query.seriesId();
            spec = spec.and((root, cq, cb) -> cb.equal(root.get("series").get("id"), seriesId));
        }
        LocalDateTime rangeFrom = from;
        if (rangeFrom != null) {
            spec = spec.and((root, cq, cb) -> cb.greaterThan(root.get("end"), rangeFrom));
        }
        LocalDateTime rangeTo = to;
        if (rangeTo != null) {
            spec = spec.and((root, cq, cb) -> cb.lessThan(root.get("start"), rangeTo));
        }

        PageRequest pageRequest = PageRequest.of(query.page(), query.size(),
                Sort.by(Sort.Order.asc("start"), Sort.Order.asc("id")));
        Page<Booking> page = bookingRepository.findAll(spec, pageRequest);
        return PageResponse.from(page, mapper::toBooking);
    }

    @Transactional
    public BookingResponse cancel(UUID id) {
        Booking booking = requireBooking(id);
        if (booking.getStatus() == BookingStatus.CONFIRMED) {
            booking.cancel();
            bookingRepository.saveAndFlush(booking);
        }
        return mapper.toBooking(booking);
    }

    @Transactional
    public void delete(UUID id) {
        Booking booking = requireBooking(id);
        bookingRepository.delete(booking);
        bookingRepository.flush();
    }

    @Transactional(readOnly = true)
    public String ics(UUID id) {
        return icsService.render(requireBooking(id));
    }

    public Booking requireBooking(UUID id) {
        return bookingRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Booking", id));
    }

    private Room lockRoom(String roomId) {
        return roomRepository.findActiveForUpdate(roomId)
                .orElseThrow(() -> new NotFoundException("Room", roomId));
    }

    private Attendees.AttendeeData validateBusinessRules(Room room, Integer attendeeCount,
                                                         List<String> attendees,
                                                         LocalDateTime start, LocalDateTime end) {
        officeHours.validateWindow(start, end);
        Attendees.AttendeeData data = Attendees.resolve(attendeeCount, attendees);
        if (data.names().size() > MAX_ATTENDEES) {
            throw new RuleViolationException("TOO_MANY_ATTENDEES",
                    "At most " + MAX_ATTENDEES + " named attendees are supported.");
        }
        Attendees.checkCapacity(data, room.getName(), room.getCapacity());
        return data;
    }

    private void assertNoOverlap(String roomId, LocalDateTime start, LocalDateTime end, UUID excludeId) {
        List<Booking> conflicts = excludeId == null
                ? bookingRepository.findOverlaps(roomId, start, end, BookingStatus.CONFIRMED)
                : bookingRepository.findOverlapsExcluding(roomId, start, end, BookingStatus.CONFIRMED, excludeId);
        if (!conflicts.isEmpty()) {
            throw new BookingConflictException(conflicts.stream().map(mapper::toConflict).toList());
        }
    }

    private void validatePaging(int page, int size) {
        if (page < 0) {
            throw new RuleViolationException("INVALID_PAGE", "page must be zero or greater.");
        }
        if (size < 1 || size > maxPageSize) {
            throw new RuleViolationException("INVALID_PAGE_SIZE",
                    "size must be between 1 and " + maxPageSize + ".");
        }
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
        return cleaned == null ? null : cleaned.toLowerCase(Locale.ROOT);
    }
}
