package com.sdsi.booking.service;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.web.dto.BookingDtos;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Stretch — operational utilization per room over a Monday-anchored week.
 *
 * <p>Denominator is bookable time only (weekdays × 09:00–18:00), so a fully booked room
 * reads 100% and weekend closure never dilutes the figure. Bookings are clipped to the
 * operating window before summing, and double-counted minutes cannot occur because the
 * write path rejects overlaps.
 */
@Service
public class UtilizationService {

    /** Minutes in one bookable day: 09:00–18:00. */
    public static final long BOOKABLE_MINUTES_PER_DAY = 540;

    private final RoomRepository rooms;
    private final BookingRepository bookings;

    public UtilizationService(RoomRepository rooms, BookingRepository bookings) {
        this.rooms = rooms;
        this.bookings = bookings;
    }

    @Transactional(readOnly = true)
    public BookingDtos.UtilizationResponse utilization(LocalDate weekStart) {
        LocalDate monday = weekStart.with(java.time.temporal.TemporalAdjusters.previousOrSame(java.time.DayOfWeek.MONDAY));
        OffsetDateTime from = monday.atTime(BusinessHours.OPEN).atOffset(BusinessHours.ZONE);
        OffsetDateTime to = monday.plusDays(7).atTime(BusinessHours.OPEN).atOffset(BusinessHours.ZONE);

        long weekdays = monday.datesUntil(monday.plusDays(7))
                .filter(d -> !BusinessHours.isWeekend(d.atTime(BusinessHours.OPEN).atOffset(BusinessHours.ZONE)))
                .count();
        long availableMinutes = weekdays * BOOKABLE_MINUTES_PER_DAY;

        Map<Long, List<Booking>> byRoom = bookings.findAllInWindow(from, to).stream()
                .collect(Collectors.groupingBy(b -> b.getRoom().getId()));

        List<BookingDtos.RoomUtilization> perRoom = new ArrayList<>();
        for (Room room : rooms.findAllByOrderByCapacityAscIdAsc()) {
            long booked = clipAndSum(byRoom.getOrDefault(room.getId(), List.of()), from, to);
            double percent = availableMinutes == 0 ? 0d : (booked * 100d) / availableMinutes;
            perRoom.add(new BookingDtos.RoomUtilization(
                    room.getId(), room.getName(), room.getCapacity(),
                    booked, availableMinutes, round2(percent)));
        }
        return new BookingDtos.UtilizationResponse(from, to, (int) BOOKABLE_MINUTES_PER_DAY, perRoom);
    }

    private long clipAndSum(List<Booking> roomBookings, OffsetDateTime from, OffsetDateTime to) {
        long total = 0;
        for (Booking b : roomBookings) {
            OffsetDateTime start = b.getStartTime().isBefore(from) ? from : b.getStartTime();
            OffsetDateTime end = b.getEndTime().isAfter(to) ? to : b.getEndTime();
            if (end.isAfter(start)) {
                total += BusinessHours.minutesBetween(start, end);
            }
        }
        return total;
    }

    private static double round2(double value) {
        return Math.round(value * 100d) / 100d;
    }
}
