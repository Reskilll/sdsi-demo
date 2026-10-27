package com.sdsi.booking.repo;

import com.sdsi.booking.domain.Room;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface RoomRepository extends JpaRepository<Room, String> {

    List<Room> findByActiveTrueOrderByCapacityAscNameAsc();

    Optional<Room> findByIdAndActiveTrue(String id);

    /**
     * Row-level lock used to serialise booking writes for one room. This is what
     * makes the "check overlaps then insert" sequence safe under concurrency.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from Room r where r.id = :id and r.active = true")
    Optional<Room> findActiveForUpdate(@Param("id") String id);
}
