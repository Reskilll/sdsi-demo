package com.sdsi.booking.repo;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.BookingStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.List;
import java.util.UUID;

public interface BookingRepository extends JpaRepository<Booking, UUID>, JpaSpecificationExecutor<Booking> {

    /**
     * Half-open interval overlap: existing.start &lt; new.end AND existing.end &gt; new.start.
     * Back-to-back bookings therefore do not overlap.
     */
    @Query("""
            select b from Booking b
            where b.room.id = :roomId
              and b.status = :status
              and b.start < :end
              and b.end > :start
            order by b.start asc
            """)
    List<Booking> findOverlaps(@Param("roomId") String roomId,
                               @Param("start") LocalDateTime start,
                               @Param("end") LocalDateTime end,
                               @Param("status") BookingStatus status);

    @Query("""
            select b from Booking b
            where b.room.id = :roomId
              and b.status = :status
              and b.start < :end
              and b.end > :start
              and b.id <> :excludeId
            order by b.start asc
            """)
    List<Booking> findOverlapsExcluding(@Param("roomId") String roomId,
                                        @Param("start") LocalDateTime start,
                                        @Param("end") LocalDateTime end,
                                        @Param("status") BookingStatus status,
                                        @Param("excludeId") UUID excludeId);

    @Query("""
            select b from Booking b
            where b.status = :status
              and b.start < :to
              and b.end > :from
            order by b.start asc
            """)
    List<Booking> findBusy(@Param("from") LocalDateTime from,
                           @Param("to") LocalDateTime to,
                           @Param("status") BookingStatus status);

    @Query("""
            select b from Booking b
            where b.room.id in :roomIds
              and b.status = :status
              and b.start < :to
              and b.end > :from
            order by b.start asc
            """)
    List<Booking> findBusyForRooms(@Param("roomIds") Collection<String> roomIds,
                                   @Param("from") LocalDateTime from,
                                   @Param("to") LocalDateTime to,
                                   @Param("status") BookingStatus status);

    @Query("""
            select b from Booking b
            where b.series.id = :seriesId
            order by b.start asc
            """)
    List<Booking> findBySeriesIdOrderByStart(@Param("seriesId") UUID seriesId);

    @Query("""
            select b from Booking b
            where b.series.id = :seriesId
              and b.status = :status
              and b.start >= :from
            order by b.start asc
            """)
    List<Booking> findSeriesOccurrencesFrom(@Param("seriesId") UUID seriesId,
                                            @Param("status") BookingStatus status,
                                            @Param("from") LocalDateTime from);
}
