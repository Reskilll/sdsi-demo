package com.sdsi.inventory;

import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.model.Reservation;
import com.sdsi.inventory.model.StockReport;
import com.sdsi.inventory.service.ErrorCode;
import com.sdsi.inventory.service.InventoryException;
import com.sdsi.inventory.service.InventoryService;
import com.sdsi.inventory.sim.FlashSaleSimulation;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Hammers the service from many threads at once and checks nothing is oversold. */
@Timeout(30)
class ConcurrencyTest {

    @RepeatedTest(5)
    void thousandsOfBuyersNeverOversell() throws Exception {
        int stock = 100;
        int buyers = 2_000;
        InventoryService service = new InventoryService(List.of(new Product("HOT", "Hot item", stock, 1)));
        AtomicInteger won = new AtomicInteger();
        AtomicInteger soldOut = new AtomicInteger();

        runConcurrently(buyers, i -> {
            try {
                Reservation r = service.reserve("u" + i, "HOT", 1);
                service.confirm("u" + i, r.id());
                won.incrementAndGet();
            } catch (InventoryException e) {
                assertEquals(ErrorCode.INSUFFICIENT_STOCK, e.code());
                soldOut.incrementAndGet();
            }
        });

        assertEquals(stock, won.get());
        assertEquals(buyers - stock, soldOut.get());
        StockReport r = service.report("HOT");
        assertEquals(0, r.available());
        assertEquals(stock, r.sold());
    }

    @RepeatedTest(5)
    void oneUserSpammingCannotBeatTheLimit() throws Exception {
        InventoryService service = new InventoryService(List.of(new Product("HOT", "Hot item", 1_000, 3)));
        AtomicInteger ok = new AtomicInteger();

        runConcurrently(500, i -> {
            try {
                service.reserve("greedy", "HOT", 1);
                ok.incrementAndGet();
            } catch (InventoryException e) {
                assertEquals(ErrorCode.PER_USER_LIMIT_EXCEEDED, e.code());
            }
        });

        assertEquals(3, ok.get());
        assertEquals(3, service.report("HOT").reserved());
    }

    @RepeatedTest(3)
    void racingConfirmAndCancelOnSameHoldAppliesExactlyOne() throws Exception {
        InventoryService service = new InventoryService(List.of(new Product("X", "x", 500, 1)));
        List<Reservation> holds = new ArrayList<>();
        for (int i = 0; i < 500; i++) {
            holds.add(service.reserve("u" + i, "X", 1));
        }
        runConcurrently(1_000, i -> {
            Reservation h = holds.get(i / 2);
            try {
                if (i % 2 == 0) {
                    service.confirm(h.userId(), h.id());
                } else {
                    service.cancel(h.userId(), h.id());
                }
            } catch (InventoryException e) {
                assertEquals(ErrorCode.INVALID_STATE, e.code());
            }
        });
        StockReport r = service.report("X");
        assertEquals(0, r.reserved());
        assertEquals(500, r.available() + r.sold());
    }

    @Test
    void sameIdempotencyKeyFromManyThreadsCreatesOneHold() throws Exception {
        InventoryService service = new InventoryService(List.of(new Product("X", "x", 100, 5)));
        Set<String> ids = java.util.concurrent.ConcurrentHashMap.newKeySet();
        runConcurrently(200, i -> ids.add(service.reserve("alice", "X", 1, null, "retry-1").id()));
        assertEquals(1, ids.size());
        assertEquals(1, service.report("X").reserved());
    }

    @Test
    void backgroundSweeperReleasesExpiredHolds() throws Exception {
        try (InventoryService service = new InventoryService(List.of(new Product("X", "x", 5, 5)))) {
            service.reserve("alice", "X", 5, Duration.ofSeconds(1), null);
            service.startExpirySweeper(Duration.ofMillis(100));
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
            while (service.report("X").available() != 5 && System.nanoTime() < deadline) {
                Thread.sleep(50);
            }
            assertEquals(5, service.report("X").available());
        }
    }

    @Test
    void simulationKeepsInvariants() throws Exception {
        FlashSaleSimulation.Result result = FlashSaleSimulation.run(
                List.of(new Product("HOT", "Hot", 50, 1)), "HOT", 3_000);
        assertTrue(result.invariantsHold());
        assertTrue(result.report().sold() <= 50);
    }

    private interface Task {
        void run(int i) throws Exception;
    }

    /** Releases all tasks at the same instant to maximise contention, then rethrows any failure. */
    private static void runConcurrently(int n, Task task) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        ConcurrentLinkedQueue<Throwable> errors = new ConcurrentLinkedQueue<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(32)) {
            List<Future<?>> futures = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                int idx = i;
                futures.add(pool.submit((Callable<Void>) () -> {
                    start.await();
                    try {
                        task.run(idx);
                    } catch (Throwable t) {
                        errors.add(t);
                    }
                    return null;
                }));
            }
            start.countDown();
            for (Future<?> f : futures) {
                f.get();
            }
        }
        if (!errors.isEmpty()) {
            Set<String> distinct = new HashSet<>();
            errors.forEach(t -> distinct.add(t.toString()));
            throw new AssertionError(errors.size() + " task(s) failed: " + distinct, errors.peek());
        }
    }
}
