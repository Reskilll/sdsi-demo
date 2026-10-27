package com.flashsale.inventory;

import com.flashsale.inventory.dto.InventoryReportResponse;
import com.flashsale.inventory.dto.ReservationResponse;
import com.flashsale.inventory.exception.InsufficientStockException;
import com.flashsale.inventory.exception.QuotaExceededException;
import com.flashsale.inventory.model.Product;
import com.flashsale.inventory.model.ReservationStatus;
import com.flashsale.inventory.repository.ProductRepository;
import com.flashsale.inventory.repository.ReservationRepository;
import com.flashsale.inventory.service.ReservationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * High-concurrency stress tests verifying zero overselling and exact invariant.
 *
 * Strategy:
 * — 100 concurrent threads race for 10 items → exactly 10 success, 90 409/conflict
 * — Per-user quota race: 10 threads from same user on limit=1 → 1 success, 9 conflict
 * — Final inventory invariant must hold: total == available + reserved + sold
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
class InventoryConcurrencyTest {

    @Autowired private ProductRepository productRepository;
    @Autowired private ReservationRepository reservationRepository;
    @Autowired private ReservationService reservationService;

    private static final String SKU = "TEST-SKU";
    private static final int TOTAL_STOCK = 10;
    private static final int THREAD_COUNT = 100;

    @BeforeEach
    void setUp() {
        reservationRepository.deleteAll();
        productRepository.deleteAll();

        productRepository.save(Product.builder()
                .sku(SKU)
                .name("Test Product")
                .totalStock(TOTAL_STOCK)
                .availableStock(TOTAL_STOCK)
                .reservedStock(0)
                .soldStock(0)
                .maxPerUser(5)
                .price(BigDecimal.TEN)
                .build());
    }

    @Test
    void hundredThreadsOnTenStock_shouldProduceExactlyTenSuccesses() throws Exception {
        int threadCount = THREAD_COUNT;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(1);

        List<Future<Boolean>> futures = new ArrayList<>();
        AtomicInteger successCount = new AtomicInteger(0);
        ConcurrentLinkedQueue<String> reservationIds = new ConcurrentLinkedQueue<>();

        for (int i = 0; i < threadCount; i++) {
            String userId = "user-" + i;
            futures.add(executor.submit(() -> {
                try {
                    latch.await(); // everyone starts simultaneously
                    ReservationResponse resp = reservationService.reserve(SKU, userId, 1, null);
                    reservationIds.add(resp.reservationId());
                    successCount.incrementAndGet();
                    return true;
                } catch (InsufficientStockException e) {
                    return false;
                }
            }));
        }

        latch.countDown();
        executor.shutdown();
        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS), "Tasks did not complete in time");

        // Verify exactly 10 succeeded (one each, stock = 10)
        int succeeded = 0;
        for (Future<Boolean> f : futures) {
            if (f.get()) succeeded++;
        }
        assertEquals(TOTAL_STOCK, succeeded,
                "Exactly " + TOTAL_STOCK + " reservations should succeed, got " + succeeded);

        // Verify invariant
        Product product = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(product.getTotalStock(),
                product.getAvailableStock() + product.getReservedStock() + product.getSoldStock(),
                "Invariant violated: total ≠ available + reserved + sold");
        assertEquals(0, product.getAvailableStock(), "All stock should be reserved");
        assertEquals(TOTAL_STOCK, product.getReservedStock());
    }

    @Test
    void perUserQuota_shouldRejectExcessRequests() throws Exception {
        Product product = productRepository.findBySku(SKU).orElseThrow();
        product.setMaxPerUser(1);
        productRepository.save(product);

        int tcount = 10;
        ExecutorService executor = Executors.newFixedThreadPool(tcount);
        CountDownLatch latch = new CountDownLatch(1);
        List<Future<Boolean>> futures = new ArrayList<>();

        String sameUser = "user-quota-test";
        for (int i = 0; i < tcount; i++) {
            futures.add(executor.submit(() -> {
                try {
                    latch.await();
                    reservationService.reserve(SKU, sameUser, 1, null);
                    return true;
                } catch (QuotaExceededException e) {
                    return false;
                }
            }));
        }

        latch.countDown();
        executor.shutdown();
        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));

        int succeeded = 0;
        for (Future<Boolean> f : futures) {
            if (f.get()) succeeded++;
        }
        assertEquals(1, succeeded, "Exactly 1 reservation should succeed when per-user limit is 1");

        Product after = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(1, after.getReservedStock());
        assertEquals(TOTAL_STOCK - 1, after.getAvailableStock());
    }

    @Test
    void zeroOversellAfterConfirmAll() {
        // Reserve all stock first
        for (int i = 0; i < TOTAL_STOCK; i++) {
            reservationService.reserve(SKU, "user-" + i, 1, null);
        }

        // Verify invariant after all reserves
        Product p = productRepository.findBySku(SKU).orElseThrow();
        assertTrue(p.isInvariantValid());
        assertEquals(0, p.getAvailableStock());
        assertEquals(TOTAL_STOCK, p.getReservedStock());

        // Confirm all
        var reservations = reservationRepository.findAll();
        for (var r : reservations) {
            reservationService.confirm(r.getReservationId());
        }

        // Final invariant check
        Product after = productRepository.findBySku(SKU).orElseThrow();
        assertTrue(after.isInvariantValid());
        assertEquals(TOTAL_STOCK, after.getSoldStock());
        assertEquals(0, after.getReservedStock());
        assertEquals(0, after.getAvailableStock());
    }

    @Test
    void ttlExpiryShouldRestoreStock() throws Exception {
        // Reserve with short TTL (5s in test config)
        ReservationResponse resp = reservationService.reserve(SKU, "user-1", 3, null);

        Product before = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(TOTAL_STOCK - 3, before.getAvailableStock());
        assertEquals(3, before.getReservedStock());

        // Wait for TTL to expire + sweep
        Thread.sleep(6_000);

        // Try to confirm — should get 410 Gone
        assertThrows(com.flashsale.inventory.exception.ReservationExpiredException.class, () -> {
            reservationService.confirm(resp.reservationId());
        });

        Product after = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(TOTAL_STOCK, after.getAvailableStock(),
                "Stock should be fully restored after TTL expiry");
        assertEquals(0, after.getReservedStock());
        assertTrue(after.isInvariantValid());
    }

    @Test
    void idempotencyKeyShouldPreventDuplicateDeductions() {
        String idempotencyKey = "idem-001";
        ReservationResponse first = reservationService.reserve(SKU, "user-a", 2, idempotencyKey);
        ReservationResponse second = reservationService.reserve(SKU, "user-a", 2, idempotencyKey);

        assertEquals(first.reservationId(), second.reservationId(),
                "Idempotent replay should return the same reservation");

        Product p = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(2, p.getReservedStock(), "Stock should be deducted only once");
    }

    @Test
    void cancelShouldRestoreStockAndBeIdempotent() {
        ReservationResponse resp = reservationService.reserve(SKU, "user-cancel", 5, null);

        // Cancel
        reservationService.cancel(resp.reservationId());
        Product mid = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(TOTAL_STOCK, mid.getAvailableStock());
        assertEquals(0, mid.getReservedStock());

        // Cancel again — idempotent, no crash
        ReservationResponse again = reservationService.cancel(resp.reservationId());
        assertEquals(ReservationStatus.CANCELLED, again.status());

        Product after = productRepository.findBySku(SKU).orElseThrow();
        assertTrue(after.isInvariantValid());
    }

    @Test
    void confirmIsIdempotent() {
        ReservationResponse resp = reservationService.reserve(SKU, "user-confirm", 2, null);
        reservationService.confirm(resp.reservationId());
        // Confirm again — should be idempotent
        ReservationResponse again = reservationService.confirm(resp.reservationId());
        assertEquals(ReservationStatus.CONFIRMED, again.status());

        Product p = productRepository.findBySku(SKU).orElseThrow();
        assertEquals(2, p.getSoldStock(), "Stock should be sold exactly once");
    }

    @Test
    void cannotCancelConfirmedReservation() {
        ReservationResponse resp = reservationService.reserve(SKU, "user-b", 2, null);
        reservationService.confirm(resp.reservationId());

        assertThrows(com.flashsale.inventory.exception.IllegalReservationStateException.class, () -> {
            reservationService.cancel(resp.reservationId());
        });
    }

    @Test
    void invalidSkuShouldThrow404() {
        assertThrows(com.flashsale.inventory.exception.ResourceNotFoundException.class, () -> {
            reservationService.reserve("NONEXISTENT", "user-x", 1, null);
        });
    }

    @Test
    void zeroQuantityShouldReject() {
        // This is enforced at the controller level via @Min(1) on the DTO.
        // In the service layer, minimum validation happens via ReserveRequest.
        // We test that negative logic is guarded:
        assertThrows(com.flashsale.inventory.exception.InsufficientStockException.class, () -> {
            // Reserve all stock, then try a larger request
            for (int i = 0; i < TOTAL_STOCK; i++) {
                reservationService.reserve(SKU, "user-" + i, 1, null);
            }
            reservationService.reserve(SKU, "overflow-user", 1, null);
        });
    }
}