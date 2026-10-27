package com.sdsi.booking.repository;

import com.sdsi.booking.domain.Room;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface RoomRepository extends JpaRepository<Room, Long> {

    /**
     * Serializes all booking mutations for a room. Every write path must take this
     * row lock before its overlap check, otherwise two transactions can both read
     * "no conflict" and both insert (double-booking race).
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from Room r where r.id = :id")
    Optional<Room> findByIdForUpdate(@Param("id") Long id);

    /** Smallest-capacity first: the find-slot best-fit ordering. */
    List<Room> findAllByOrderByCapacityAscIdAsc();

    Optional<Room> findByName(String name);
}
