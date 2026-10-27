package com.sdsi.inventory.sim;

import com.sdsi.inventory.model.Product;
import com.sdsi.inventory.model.Reservation;
import com.sdsi.inventory.model.StockReport;
import com.sdsi.inventory.service.ErrorCode;
import com.sdsi.inventory.service.InventoryException;
import com.sdsi.inventory.service.InventoryService;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.LongAdder;

/**
 * Stress demo: N buyers hit one SKU at the same instant. Each tries to reserve 1 unit and then
 * confirms (70%), cancels (20%) or abandons the hold (10%). Prints outcomes and proves no oversell.
 */
public final class FlashSaleSimulation {

    private FlashSaleSimulation() {
    }

    public static Result run(List<Product> products, String sku, int buyers) throws InterruptedException {
        if (buyers <= 0) {
            throw new IllegalArgumentException("buyers must be positive");
        }
        Map<ErrorCode, LongAdder> failures = new ConcurrentHashMap<>();
        LongAdder confirmed = new LongAdder();
        LongAdder cancelled = new LongAdder();
        LongAdder abandoned = new LongAdder();

        try (InventoryService service = new InventoryService(products)) {
            StockReport before = service.report(sku);
            CountDownLatch start = new CountDownLatch(1);
            long t0;
            try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < buyers; i++) {
                    String user = "buyer-" + i;
                    pool.submit(() -> {
                        start.await();
                        try {
                            Reservation r = service.reserve(user, sku, 1);
                            int roll = ThreadLocalRandom.current().nextInt(10);
                            if (roll < 7) {
                                service.confirm(user, r.id());
                                confirmed.increment();
                            } else if (roll < 9) {
                                service.cancel(user, r.id());
                                cancelled.increment();
                            } else {
                                abandoned.increment();
                            }
                        } catch (InventoryException e) {
                            failures.computeIfAbsent(e.code(), c -> new LongAdder()).increment();
                        }
                        return null;
                    });
                }
                t0 = System.nanoTime();
                start.countDown();
            }
            long elapsedMs = (System.nanoTime() - t0) / 1_000_000;
            StockReport after = service.report(sku);

            System.out.printf("Flash sale on %s: %d buyers, %d units in stock%n", sku, buyers, before.total());
            System.out.printf("  confirmed=%d cancelled=%d abandoned(held)=%d rejected=%s%n",
                    confirmed.sum(), cancelled.sum(), abandoned.sum(), failures);
            System.out.printf("  final: available=%d reserved=%d sold=%d (took %d ms)%n",
                    after.available(), after.reserved(), after.sold(), elapsedMs);
            boolean ok = after.sold() <= after.total()
                    && after.available() + after.reserved() + after.sold() == after.total()
                    && after.sold() == confirmed.sum();
            System.out.println(ok ? "  OK: no overselling, counts reconcile." : "  FAIL: invariant violated!");
            return new Result(after, confirmed.sum(), ok);
        }
    }

    public record Result(StockReport report, long confirmed, boolean invariantsHold) {
    }
}
