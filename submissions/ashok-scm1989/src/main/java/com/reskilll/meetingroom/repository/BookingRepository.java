package com.reskilll.meetingroom.repository;

import com.reskilll.meetingroom.model.Booking;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface BookingRepository extends JpaRepository<Booking, String> {

    /**
     * Checks if any booking overlaps with [startTime, endTime) on roomId.
     * Back-to-back bookings (where end == start or start == end) are allowed.
     * Overlap occurs when: b.startTime < :endTime AND b.endTime > :startTime.
     */
    @Query("SELECT b FROM Booking b WHERE b.roomId = :roomId " +
           "AND b.startTime < :endTime AND b.endTime > :startTime " +
           "AND (:excludeBookingId IS NULL OR b.id <> :excludeBookingId) " +
           "ORDER BY b.startTime ASC")
    List<Booking> findConflictingBookings(@Param("roomId") String roomId,
                                         @Param("startTime") LocalDateTime startTime,
                                         @Param("endTime") LocalDateTime endTime,
                                         @Param("excludeBookingId") String excludeBookingId);

    /**
     * Finds all bookings for a room overlapping a given time window (e.g. 09:00 to 18:00 on a specific day).
     */
    @Query("SELECT b FROM Booking b WHERE b.roomId = :roomId " +
           "AND b.startTime < :windowEnd AND b.endTime > :windowStart " +
           "ORDER BY b.startTime ASC")
    List<Booking> findBookingsInWindow(@Param("roomId") String roomId,
                                      @Param("windowStart") LocalDateTime windowStart,
                                      @Param("windowEnd") LocalDateTime windowEnd);

    List<Booking> findByRoomIdOrderByStartTimeAsc(String roomId);

    List<Booking> findByOrganiserOrderByStartTimeAsc(String organiser);

    List<Booking> findByStartTimeBetweenOrderByStartTimeAsc(LocalDateTime start, LocalDateTime end);

    List<Booking> findByRecurrenceGroupIdOrderByOccurrenceIndexAsc(String recurrenceGroupId);

    long deleteByRecurrenceGroupId(String recurrenceGroupId);
}
