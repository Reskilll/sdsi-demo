package com.sdsi.booking.repo;

import com.sdsi.booking.domain.BookingSeries;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

import java.util.UUID;

public interface BookingSeriesRepository extends JpaRepository<BookingSeries, UUID>, JpaSpecificationExecutor<BookingSeries> {
}
