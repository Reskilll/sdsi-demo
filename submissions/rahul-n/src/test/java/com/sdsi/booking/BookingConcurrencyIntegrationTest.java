package com.sdsi.booking;

import com.sdsi.booking.domain.Booking;
import com.sdsi.booking.domain.Room;
import com.sdsi.booking.repository.BookingRepository;
import com.sdsi.booking.repository.RoomRepository;
import com.sdsi.booking.service.BookingService;
import com.sdsi.booking.web.dto.BookingDtos;
import com.sdsi.booking.web.error.ApiException;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.PessimisticLockingFailureException;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Proves the {@code PESSIMISTIC_WRITE} row lock eliminates double-booking under real
 * contention. These tests deliberately run outside a test transaction so every attempt
 * commits (or fails) on its own — rolling back would hide the race entirely.
 *
 * <p>Each test uses its own room and day so the committed rows cannot interfere.
 */
@SpringBootTest
class BookingConcurrencyIntegrationTest {

    private static final int THREADS = 12;

    @Autowired
    private BookingService service;

    @Autowired
    private RoomRepository rooms;

    @Autowired
    private BookingRepository bookings;

    @Test
    @DisplayName("Concurrency: 12 simultaneous bookings of the same slot yield exactly one winner")
    void simultaneousBookingsOfSameSlot_yieldSingleWinner() throws Exception {
        Room room = rooms.findByName("Room C").orElseThrow();
        OffsetDateTime start = at(LocalDate.of(2026, 11, 2), 9, 0);
        OffsetDateTime end = start.plusHours(1);
        BookingDtos.BookingRequest request =
                new BookingDtos.BookingRequest(room.getId(), "Contended", start, end, List.of("a"));

        List<Attempt> attempts = runConcurrently(THREADS, () -> service.create(request));

        List<Attempt> winners = attempts.stream().filter(Attempt::succeeded).toList();
        assertThat(winners).as("exactly one caller may win the slot").hasSize(1);

        List<Attempt> losers = attempts.stream().filter(a -> !a.succeeded()).toList();
        assertThat(losers).allSatisfy(a -> assertThat(a.failure())
                .as("every loser must be rejected as a conflict, never a crash")
                .isInstanceOf(ApiException.Conflict.class));

        assertThat(bookings.findOverlapping(room.getId(), start, end))
                .as("the database holds exactly one booking for the contended slot")
                .hasSize(1);
    }

    @Test
    @DisplayName("Concurrency: overlapping random slots in one room never produce a double-booking")
    void overlappingRandomSlots_neverDoubleBook() throws Exception {
        Room room = rooms.findByName("Room C").orElseThrow();
        LocalDate day = LocalDate.of(2026, 11, 3);
        ThreadLocalRandom random = ThreadLocalRandom.current();

        List<Callable<Object>> jobs = new ArrayList<>();
        for (int i = 0; i < THREADS * 2; i++) {
            int hour = random.nextInt(9, 16);
            int minute = random.nextBoolean() ? 0 : 30;
            int durationMinutes = random.nextBoolean() ? 60 : 120;
            OffsetDateTime start = at(day, hour, minute);
            BookingDtos.BookingRequest request = new BookingDtos.BookingRequest(
                    room.getId(), "Racer-" + i, start, start.plusMinutes(durationMinutes), List.of("a"));
            jobs.add(() -> {
                try {
                    service.create(request);
                } catch (ApiException.Conflict | PessimisticLockingFailureException expected) {
                    // Losing the race is a legitimate outcome; the invariant below is what matters.
                }
                return null;
            });
        }

        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        try {
            CountDownLatch gate = new CountDownLatch(1);
            List<Future<Object>> futures = jobs.stream()
                    .map(job -> pool.submit(() -> {
                        gate.await();
                        return job.call();
                    }))
                    .toList();
            gate.countDown();
            for (Future<Object> future : futures) {
                future.get(60, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }

        List<Booking> persisted = bookings.findByRoom_IdOrderByStartTimeAsc(room.getId());
        assertThat(persisted).isNotEmpty();
        for (int i = 0; i < persisted.size(); i++) {
            for (int j = i + 1; j < persisted.size(); j++) {
                Booking left = persisted.get(i);
                Booking right = persisted.get(j);
                assertThat(left.overlaps(right.getStartTime(), right.getEndTime()))
                        .as("bookings %s and %s must not overlap", left.getStartTime(), right.getStartTime())
                        .isFalse();
            }
        }
    }

    @Test
    @DisplayName("Concurrency: contending back-to-back bookings both commit — the lock is not over-serialising")
    void contendingBackToBackBookings_bothSucceed() throws Exception {
        Room room = rooms.findByName("Room B").orElseThrow();
        LocalDate day = LocalDate.of(2026, 11, 4);
        OffsetDateTime boundary = at(day, 10, 0);

        BookingDtos.BookingRequest before =
                new BookingDtos.BookingRequest(room.getId(), "Before", boundary.minusHours(1), boundary, List.of("a"));
        BookingDtos.BookingRequest after =
                new BookingDtos.BookingRequest(room.getId(), "After", boundary, boundary.plusHours(1), List.of("b"));

        CountDownLatch gate = new CountDownLatch(1);
        AtomicInteger success = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            List<Future<Integer>> futures = List.of(before, after).stream()
                    .map(request -> pool.submit(() -> {
                        gate.await();
                        service.create(request);
                        return success.incrementAndGet();
                    }))
                    .toList();
            gate.countDown();
            for (Future<Integer> future : futures) {
                future.get(30, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }

        assertThat(success.get()).as("touching intervals are both legal").isEqualTo(2);
        assertThat(bookings.findOverlapping(room.getId(), boundary.minusHours(1), boundary.plusHours(1))).hasSize(2);
    }

    // ---------------------------------------------------------------- helpers

    private record Attempt(BookingDtos.BookingResponse response, Throwable failure) {
        boolean succeeded() {
            return failure == null;
        }
    }

    /** Fires {@code count} copies of {@code job} from a released gate to maximise contention. */
    private List<Attempt> runConcurrently(int count, Callable<BookingDtos.BookingResponse> job) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(count);
        try {
            CountDownLatch gate = new CountDownLatch(1);
            List<Future<Attempt>> futures = new ArrayList<>();
            for (int i = 0; i < count; i++) {
                futures.add(pool.submit(() -> {
                    gate.await();
                    try {
                        return new Attempt(job.call(), null);
                    } catch (Throwable t) {
                        return new Attempt(null, t);
                    }
                }));
            }
            gate.countDown();
            List<Attempt> attempts = new ArrayList<>();
            for (Future<Attempt> future : futures) {
                attempts.add(future.get(60, TimeUnit.SECONDS));
            }
            return attempts;
        } finally {
            pool.shutdownNow();
        }
    }

    private static OffsetDateTime at(LocalDate date, int hour, int minute) {
        return date.atTime(hour, minute).atOffset(ZoneOffset.UTC);
    }
}
