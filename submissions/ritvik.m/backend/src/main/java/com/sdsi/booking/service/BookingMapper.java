package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.BookingSeries;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.web.dto.BookingResponse;
import com.sdsi.booking.web.dto.ConflictView;
import com.sdsi.booking.web.dto.RoomResponse;
import com.sdsi.booking.web.dto.SeriesResponse;
import com.sdsi.booking.web.dto.SeriesSummaryResponse;
import org.springframework.stereotype.Component;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

@Component
public class BookingMapper {

    public RoomResponse toRoom(Room room) {
        Set<String> amenities = new LinkedHashSet<>(new TreeSet<>(room.getAmenities()));
        return new RoomResponse(room.getId(), room.getName(), room.getCapacity(),
                room.getFloor(), room.getLocation(), amenities);
    }

    public BookingResponse toBooking(Booking booking) {
        return new BookingResponse(
                booking.getId(),
                toRoom(booking.getRoom()),
                booking.getOrganiser(),
                booking.getOrganiserEmail(),
                booking.getTitle(),
                booking.getDescription(),
                booking.getStart(),
                booking.getEnd(),
                booking.getAttendeeCount(),
                new LinkedHashSet<>(new TreeSet<>(booking.getAttendees())),
                booking.getStatus(),
                booking.getSeries() == null ? null : booking.getSeries().getId(),
                booking.getOccurrenceIndex(),
                booking.getCreatedAt(),
                booking.getUpdatedAt(),
                booking.getVersion());
    }

    public ConflictView toConflict(Booking booking) {
        return new ConflictView(booking.getId(), booking.getTitle(), booking.getOrganiser(),
                booking.getStart(), booking.getEnd());
    }

    public SeriesSummaryResponse toSeriesSummary(BookingSeries series) {
        return new SeriesSummaryResponse(
                series.getId(),
                toRoom(series.getRoom()),
                series.getOrganiser(),
                series.getOrganiserEmail(),
                series.getTitle(),
                series.getDescription(),
                series.getStartTime(),
                series.getEndTime(),
                series.getStartsOn(),
                series.getWeeks(),
                List.copyOf(series.dayOfWeekSet()),
                series.getAttendeeCount(),
                new LinkedHashSet<>(new TreeSet<>(series.getAttendees())),
                series.getCreatedAt());
    }

    public SeriesResponse toSeries(BookingSeries series, List<Booking> occurrences) {
        return new SeriesResponse(
                series.getId(),
                toRoom(series.getRoom()),
                series.getOrganiser(),
                series.getOrganiserEmail(),
                series.getTitle(),
                series.getDescription(),
                series.getStartTime(),
                series.getEndTime(),
                series.getStartsOn(),
                series.getWeeks(),
                List.copyOf(series.dayOfWeekSet()),
                series.getAttendeeCount(),
                new LinkedHashSet<>(new TreeSet<>(series.getAttendees())),
                series.getCreatedAt(),
                occurrences.stream().map(this::toBooking).toList());
    }
}
