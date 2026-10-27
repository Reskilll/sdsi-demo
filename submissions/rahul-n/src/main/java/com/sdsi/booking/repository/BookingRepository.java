package com.sdsi.booking.repository;

import com.sdsi.booking.domain.Booking;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.OffsetDateTime;
import java.util.List;

public interface BookingRepository extends JpaRepository<Booking, Long> {

    /**
     * Half-open overlap: an existing booking conflicts iff
     * {@code existing.start < requestedEnd AND existing.end > requestedStart}.
     * Back-to-back intervals (09:00-10:00 then 10:00-11:00) therefore never conflict.
     */
    @Query("""
            select b from Booking b
            where b.room.id = :roomId
              and b.startTime < :end
              and b.endTime > :start
            order by b.startTime asc
            """)
    List<Booking> findOverlapping(@Param("roomId") Long roomId,
                                  @Param("start") OffsetDateTime start,
                                  @Param("end") OffsetDateTime end);

    @Query("""
            select b from Booking b
            where b.room.id = :roomId
              and b.startTime < :to
              and b.endTime > :from
            order by b.startTime asc
            """)
    List<Booking> findInWindow(@Param("roomId") Long roomId,
                               @Param("from") OffsetDateTime from,
                               @Param("to") OffsetDateTime to);

    @Query("""
            select b from Booking b
            where b.startTime < :to
              and b.endTime > :from
            order by b.startTime asc
            """)
    List<Booking> findAllInWindow(@Param("from") OffsetDateTime from, @Param("to") OffsetDateTime to);

    List<Booking> findByRoom_IdOrderByStartTimeAsc(Long roomId);
}
