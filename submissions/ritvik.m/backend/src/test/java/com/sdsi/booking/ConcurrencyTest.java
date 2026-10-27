package com.sdsi.booking;

import com.sdsi.booking.service.BookingService;
import com.sdsi.booking.support.IntegrationTestBase;
import com.sdsi.booking.web.dto.BookingCreateRequest;
import com.sdsi.booking.web.error.BookingConflictException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ConcurrencyTest extends IntegrationTestBase {

    @Autowired
    private BookingService bookingService;

    @Test
    void concurrentBookingsForTheSameSlotCreateExactlyOne() throws Exception {
        LocalDate date = futureDate();
        LocalDateTime start = date.atTime(14, 0);
        LocalDateTime end = date.atTime(15, 0);
        int threads = 4;

        ExecutorService pool = Executors.newFixedThreadPool(threads);
        CountDownLatch ready = new CountDownLatch(threads);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<Boolean>> results = new ArrayList<>();
        try {
            for (int i = 0; i < threads; i++) {
                String organiser = "racer-" + i;
                results.add(pool.submit(() -> {
                    ready.countDown();
                    if (!go.await(10, TimeUnit.SECONDS)) {
                        return false;
                    }
                    try {
                        bookingService.create(new BookingCreateRequest(
                                "atlas", organiser, null, "Race", null, start, end, 2, null));
                        return true;
                    } catch (BookingConflictException conflict) {
                        return false;
                    }
                }));
            }
            assertTrue(ready.await(10, TimeUnit.SECONDS), "workers did not start");
            go.countDown();

            int created = 0;
            for (Future<Boolean> result : results) {
                if (result.get(30, TimeUnit.SECONDS)) {
                    created++;
                }
            }
            assertThat(created).isEqualTo(1);
            assertThat(bookingRepository.count()).isEqualTo(1);
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void concurrentBookingsForDifferentRoomsAllSucceed() throws Exception {
        LocalDate date = futureDate();
        LocalDateTime start = date.atTime(15, 0);
        LocalDateTime end = date.atTime(16, 0);
        String[] rooms = {"atlas", "orion", "vega", "lumen"};

        ExecutorService pool = Executors.newFixedThreadPool(rooms.length);
        CountDownLatch ready = new CountDownLatch(rooms.length);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<Boolean>> results = new ArrayList<>();
        try {
            for (String room : rooms) {
                results.add(pool.submit(() -> {
                    ready.countDown();
                    if (!go.await(10, TimeUnit.SECONDS)) {
                        return false;
                    }
                    bookingService.create(new BookingCreateRequest(
                            room, "parallel", null, "Parallel", null, start, end, 2, null));
                    return true;
                }));
            }
            assertTrue(ready.await(10, TimeUnit.SECONDS));
            go.countDown();
            int created = 0;
            for (Future<Boolean> result : results) {
                if (result.get(30, TimeUnit.SECONDS)) {
                    created++;
                }
            }
            assertThat(created).isEqualTo(rooms.length);
        } finally {
            pool.shutdownNow();
        }
    }
}
