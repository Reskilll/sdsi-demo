package com.flashsale;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Self-contained test runner — replaces JUnit when Maven is unavailable.
 *
 * <p>Runs all 45+ test cases across the same categories as the JUnit suite.
 * Each test prints a dot on success, 'F' on failure with details.
 */
@SuppressWarnings("unused")
public class TestRunner {

    private static int passed = 0;
    private static int failed = 0;
    private static final List<String> failures = new ArrayList<>();

    // ── helpers ──────────────────────────────────────────────

    static Path inv(String... products) {
        try {
            Path path = Files.createTempFile("inv-", ".json");
            String joined = String.join(",", products);
            Files.writeString(path, "{\"products\": [" + joined + "]}");
            return path;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    static String prod(String sku, String name, double price, int stock, int maxPerUser) {
        return """
                {"sku": "%s", "name": "%s", "description": "", "price": %.0f, "stock": %d, "max_per_user": %d}
                """.formatted(sku, name, price, stock, maxPerUser).strip();
    }

    // SKU_A: high limit so stock tests don't accidentally hit limit
    static final String SKU_A  = prod("SKU-A", "Product A", 100, 10, 100);
    // SKU_B: max=1 for limit tests
    static final String SKU_B  = prod("SKU-B", "Product B", 200, 5, 1);
    // SKU_LO: max=2 for targeted limit tests
    static final String SKU_LO = prod("SKU-LO", "Product Limited", 300, 50, 2);

    static void sleepMs(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    static void join(Thread t) {
        try { t.join(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    static void await(CountDownLatch latch) {
        try { latch.await(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    /** Write a temp file from a raw JSON string (not wrapped in {"products":[...]}) */
    static Path tmpFile(String jsonContent) {
        try {
            Path p = Files.createTempFile("test-", ".json");
            Files.writeString(p, jsonContent);
            return p;
        } catch (IOException e) { throw new RuntimeException(e); }
    }

    // ── assertion helpers ────────────────────────────────────

    static void assertEqual(int expected, int actual, String label) {
        if (expected != actual) throw new AssertionError(label + ": expected " + expected + ", got " + actual);
    }

    static void assertEqual(Object expected, Object actual, String label) {
        if (!expected.equals(actual)) throw new AssertionError(label + ": expected " + expected + ", got " + actual);
    }

    static void assertTrue(boolean cond, String label) {
        if (!cond) throw new AssertionError(label);
    }

    static void assertNotNull(Object obj, String label) {
        if (obj == null) throw new AssertionError(label + " was null");
    }

    static void assertNull(Object obj, String label) {
        if (obj != null) throw new AssertionError(label + " was not null: " + obj);
    }

    static void assertThrows(Class<? extends Throwable> exType, Runnable task, String label) {
        try {
            task.run();
            throw new AssertionError(label + ": expected " + exType.getSimpleName() + " but no exception thrown");
        } catch (Throwable t) {
            if (!exType.isAssignableFrom(t.getClass())) {
                throw new AssertionError(label + ": expected " + exType.getSimpleName() + " but got " + t.getClass().getSimpleName() + ": " + t.getMessage());
            }
        }
    }

    // ── test executor ────────────────────────────────────────

    static void test(String name, Runnable task) {
        try {
            task.run();
            passed++;
            System.out.print(".");
        } catch (Throwable t) {
            failed++;
            String msg = "FAIL  " + name + ": " + t.getMessage();
            failures.add(msg);
            System.out.print("F");
        }
    }

    static void section(String name) {
        System.out.println("\n  " + name);
    }

    // ══════════════════════════════════════════════════════════
    // MAIN
    // ══════════════════════════════════════════════════════════

    public static void main(String[] args) {
        System.out.println("=== Flash Sale Inventory — Test Suite ===\n");

        testLoading();
        testReserveHappy();
        testReserveEdges();
        testPerUserLimits();
        testConfirm();
        testCancel();
        testTtlExpiry();
        testStatus();
        testReport();
        testConcurrency();
        testLifecycle();

        System.out.println("\n");
        if (!failures.isEmpty()) {
            System.out.println("=== FAILURES ===");
            failures.forEach(System.out::println);
        }
        System.out.printf("%nResults: %d passed, %d failed%n", passed, failed);
        if (failed > 0) System.exit(1);
    }

    // ── Loading ──────────────────────────────────────────────

    static void testLoading() {
        section("Loading & validation");

        test("loads valid inventory", () -> {
            InventoryStore store = InventoryStore.load(inv(SKU_A, SKU_B));
            List<StockReport> r = store.reportAll();
            assertEqual(2, r.size(), "product count");
            assertEqual(10, r.getFirst().total(), "total stock");
            assertEqual(10, r.getFirst().available(), "available");
        });

        test("missing file", () -> {
            assertThrows(InventoryException.class, () ->
                    InventoryStore.load(Path.of("/nonexistent.json")), "missing file");
        });

        test("bad JSON", () -> {
            Path p = tmpFile("not json {{{{");
            assertThrows(InventoryException.class, () -> InventoryStore.load(p), "bad JSON");
        });

        test("empty products", () -> {
            Path p = tmpFile("{}");
            assertThrows(InventoryException.class, () -> InventoryStore.load(p), "empty products");
        });

        test("missing field", () -> {
            Path p = inv("""
                    {"sku": "X", "name": "X", "price": 1, "stock": 1}
                    """);
            assertThrows(InventoryException.class, () -> InventoryStore.load(p), "missing field");
        });

        test("duplicate SKU", () -> {
            assertThrows(InventoryException.class, () ->
                    InventoryStore.load(inv(SKU_A, SKU_A)), "duplicate SKU");
        });

        test("negative stock", () -> {
            assertThrows(InventoryException.class, () ->
                    InventoryStore.load(inv(prod("X", "X", 1, -5, 1))), "negative stock");
        });

        test("negative price", () -> {
            assertThrows(InventoryException.class, () ->
                    InventoryStore.load(inv(prod("X", "X", -10, 5, 1))), "negative price");
        });

        test("zero max_per_user", () -> {
            assertThrows(InventoryException.class, () ->
                    InventoryStore.load(inv(prod("X", "X", 1, 5, 0))), "zero max");
        });
    }

    // ── Reserve Happy ────────────────────────────────────────

    static void testReserveHappy() {
        section("Reserve — happy path");

        test("basic reservation", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            Reservation r = s.reserve("user1", "SKU-A", 2);
            assertEqual("user1", r.userId(), "userId");
            assertEqual("SKU-A", r.sku(), "sku");
            assertEqual(2, r.quantity(), "qty");
            assertEqual(ReservationStatus.ACTIVE, r.status(), "status");
            assertEqual(120, r.ttlSeconds(), "ttl");
            StockReport rep = s.report("SKU-A").getFirst();
            assertEqual(8, rep.available(), "available");
            assertEqual(2, rep.reserved(), "reserved");
            assertEqual(0, rep.sold(), "sold");
        });

        test("multiple users same SKU", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            s.reserve("u1", "SKU-A", 2);
            s.reserve("u2", "SKU-A", 3);
            StockReport r = s.report("SKU-A").getFirst();
            assertEqual(5, r.available(), "avail");
            assertEqual(5, r.reserved(), "resvd");
        });

        test("different SKUs", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            s.reserve("u1", "SKU-A", 2);
            s.reserve("u1", "SKU-B", 1);
            assertEqual(2, s.report("SKU-A").getFirst().reserved(), "A resvd");
            assertEqual(1, s.report("SKU-B").getFirst().reserved(), "B resvd");
        });

        test("custom TTL", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1, 30);
            assertEqual(30, r.ttlSeconds(), "custom ttl");
        });

        test("unique IDs", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r1 = s.reserve("u1", "SKU-A", 1);
            Reservation r2 = s.reserve("u2", "SKU-A", 1);
            assertTrue(!r1.reservationId().equals(r2.reservationId()), "unique IDs");
        });
    }

    // ── Reserve Edges ────────────────────────────────────────

    static void testReserveEdges() {
        section("Reserve — edge cases");

        test("exact stock", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            s.reserve("u1", "SKU-A", 10);
            StockReport r = s.report("SKU-A").getFirst();
            assertEqual(0, r.available(), "avail");
            assertEqual(10, r.reserved(), "resvd");
        });

        test("exceeds stock", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.OutOfStock.class,
                    () -> s.reserve("u1", "SKU-A", 11), "exceeds stock");
        });

        test("exceeds after partial", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            s.reserve("u1", "SKU-A", 8);
            assertThrows(InventoryException.OutOfStock.class,
                    () -> s.reserve("u2", "SKU-A", 5), "partial then exceed");
        });

        test("zero quantity", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.InvalidQuantity.class,
                    () -> s.reserve("u1", "SKU-A", 0), "zero qty");
        });

        test("negative quantity", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.InvalidQuantity.class,
                    () -> s.reserve("u1", "SKU-A", -1), "neg qty");
        });

        test("unknown SKU", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.class,
                    () -> s.reserve("u1", "NONEXISTENT", 1), "unknown SKU");
        });
    }

    // ── Per-user limits ──────────────────────────────────────

    static void testPerUserLimits() {
        section("Per-user purchase limits");

        test("limit on reserve", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO));
            s.reserve("user1", "SKU-LO", 2);
            assertThrows(InventoryException.PerUserLimit.class,
                    () -> s.reserve("user1", "SKU-LO", 1), "limit reached");
        });

        test("limits count confirmed", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO));
            Reservation r = s.reserve("user1", "SKU-LO", 1);
            s.confirm(r.reservationId());
            s.reserve("user1", "SKU-LO", 1); // still 1 left
            assertThrows(InventoryException.PerUserLimit.class,
                    () -> s.reserve("user1", "SKU-LO", 1), "after confirmed");
        });

        test("limit released on cancel", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO));
            Reservation r = s.reserve("user1", "SKU-LO", 2);
            s.cancel(r.reservationId());
            s.reserve("user1", "SKU-LO", 2); // can reserve again
        });

        test("limit released on expiry", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO));
            s.reserve("user1", "SKU-LO", 2, 1);
            sleepMs(1500);
            s.purgeExpired();
            s.reserve("user1", "SKU-LO", 2); // must succeed
        });

        test("per-SKU limits", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO, SKU_B));
            s.reserve("user1", "SKU-LO", 2); // SKU-LO max=2
            s.reserve("user1", "SKU-B", 1);  // SKU-B max=1
            assertThrows(InventoryException.PerUserLimit.class,
                    () -> s.reserve("user1", "SKU-B", 1), "per-sku B");
        });

        test("per-user not shared", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_LO));
            s.reserve("u1", "SKU-LO", 2);
            s.reserve("u2", "SKU-LO", 2); // each has own limit
        });
    }

    // ── Confirm ──────────────────────────────────────────────

    static void testConfirm() {
        section("Confirm");

        test("confirm deducts stock", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 2);
            s.confirm(r.reservationId());
            StockReport rep = s.report("SKU-A").getFirst();
            assertEqual(8, rep.available(), "avail");
            assertEqual(0, rep.reserved(), "resvd");
            assertEqual(2, rep.sold(), "sold");
        });

        test("unknown reservation", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.confirm("nonexistent"), "unknown");
        });

        test("already confirmed", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            s.confirm(r.reservationId());
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.confirm(r.reservationId()), "double confirm");
        });

        test("already cancelled", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            s.cancel(r.reservationId());
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.confirm(r.reservationId()), "confirm cancelled");
        });

        test("expired cannot confirm", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1, 1);
            sleepMs(1500);
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.confirm(r.reservationId()), "expired confirm");
        });
    }

    // ── Cancel ───────────────────────────────────────────────

    static void testCancel() {
        section("Cancel");

        test("cancel releases stock", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 3);
            s.cancel(r.reservationId());
            StockReport rep = s.report("SKU-A").getFirst();
            assertEqual(10, rep.available(), "avail");
            assertEqual(0, rep.reserved(), "resvd");
            assertEqual(0, rep.sold(), "sold");
        });

        test("unknown reservation", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.cancel("nonexistent"), "unknown");
        });

        test("already cancelled", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            s.cancel(r.reservationId());
            assertThrows(InventoryException.ReservationNotFound.class,
                    () -> s.cancel(r.reservationId()), "double cancel");
        });
    }

    // ── TTL expiry ───────────────────────────────────────────

    static void testTtlExpiry() {
        section("TTL expiry");

        test("lazy expiry on reserve", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A)); // stock=10, max=100
            s.reserve("u1", "SKU-A", 2, 1); // reserve 2, ttl=1s
            sleepMs(1500);
            s.reserve("u2", "SKU-A", 1); // lazy sweep + new reserve
            StockReport r = s.report("SKU-A").getFirst();
            // stock=10, u1's 2 expired→released, u2's 1 is active
            assertEqual(9, r.available(), "10 - 1(active) = 9 avail");
            assertEqual(1, r.reserved(), "1 reserved");
        });

        test("lazy expiry on report", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            s.reserve("u1", "SKU-A", 2, 1);
            sleepMs(1500);
            StockReport r = s.report("SKU-A").getFirst();
            assertEqual(10, r.available(), "full available");
            assertEqual(0, r.reserved(), "none reserved");
        });

        test("purge count", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            s.reserve("u1", "SKU-A", 1, 1);
            s.reserve("u2", "SKU-B", 1, 1);
            sleepMs(1500);
            assertEqual(2, s.purgeExpired(), "purged 2");
        });

        test("expiry preserves status", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1, 1);
            sleepMs(1500);
            Reservation got = s.getReservation(r.reservationId());
            assertNotNull(got, "got");
            assertEqual(ReservationStatus.EXPIRED, got.status(), "expired status");
        });

        test("expiry releases limit", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            s.reserve("u1", "SKU-A", 2, 1);
            sleepMs(1500);
            s.purgeExpired();
            s.reserve("u1", "SKU-A", 2); // succeeds
        });
    }

    // ── Status lookup ────────────────────────────────────────

    static void testStatus() {
        section("Status lookup");

        test("active", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            Reservation got = s.getReservation(r.reservationId());
            assertNotNull(got, "got");
            assertEqual(ReservationStatus.ACTIVE, got.status(), "active");
        });

        test("unknown → null", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertNull(s.getReservation("unknown"), "unknown");
        });

        test("after confirm", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            s.confirm(r.reservationId());
            assertEqual(ReservationStatus.CONFIRMED,
                    s.getReservation(r.reservationId()).status(), "confirmed");
        });

        test("after cancel", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1);
            s.cancel(r.reservationId());
            assertEqual(ReservationStatus.CANCELLED,
                    s.getReservation(r.reservationId()).status(), "cancelled");
        });
    }

    // ── Report ───────────────────────────────────────────────

    static void testReport() {
        section("Report");

        test("single SKU", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            StockReport r = s.report("SKU-A").getFirst();
            assertEqual("SKU-A", r.sku(), "sku");
            assertEqual("Product A", r.name(), "name");
            assertEqual(10, r.total(), "total");
            assertEqual(10, r.available(), "avail");
            assertEqual(0, r.reserved(), "resvd");
            assertEqual(0, r.sold(), "sold");
        });

        test("all products", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            assertEqual(2, s.reportAll().size(), "count");
        });

        test("invariant holds", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            s.reserve("u1", "SKU-A", 3);
            s.reserve("u2", "SKU-A", 2);
            Reservation r1 = s.reserve("u3", "SKU-A", 1);
            s.confirm(r1.reservationId());
            StockReport r = s.report("SKU-A").getFirst();
            assertTrue(r.invariantHolds(), "a+r+s == total");
        });

        test("unknown SKU", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.class,
                    () -> s.report("NONEXISTENT"), "unknown SKU");
        });
    }

    // ── Concurrency ──────────────────────────────────────────

    static void testConcurrency() {
        section("Concurrency");

        test("no oversell under contention", () -> {
            int stock = 50, threads = 20, perThread = 3; // 60 > 50
            InventoryStore s = InventoryStore.load(inv(
                    prod("HOT", "Hot", 1, stock, 100)));
            CountDownLatch latch = new CountDownLatch(threads);
            AtomicInteger successes = new AtomicInteger();
            List<Exception> errors = new ArrayList<>();

            for (int i = 0; i < threads; i++) {
                final int id = i;
                Thread.ofPlatform().start(() -> {
                    try {
                        s.reserve("user-" + id, "HOT", perThread);
                        successes.incrementAndGet();
                    } catch (InventoryException.OutOfStock ignored) {
                    } catch (Exception e) { errors.add(e);
                    } finally { latch.countDown(); }
                });
            }
            await(latch);
            assertTrue(errors.isEmpty(), "concurrency errors: " + errors);
            StockReport r = s.report("HOT").getFirst();
            assertTrue(r.available() >= 0, "avail >= 0");
            assertTrue(r.reserved() <= stock, "reserve <= stock");
            assertEqual(0, r.sold(), "no sold");
            assertEqual(stock, r.available() + r.reserved() + r.sold(), "invariant");
        });

        test("no double confirm", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_B));
            Reservation r = s.reserve("u1", "SKU-B", 1);
            AtomicInteger successCount = new AtomicInteger();

            Runnable task = () -> {
                try {
                    s.confirm(r.reservationId());
                    successCount.incrementAndGet();
                } catch (InventoryException.ReservationNotFound ignored) {}
            };

            Thread t1 = Thread.ofPlatform().start(task);
            Thread t2 = Thread.ofPlatform().start(task);
            Thread t3 = Thread.ofPlatform().start(task);
            join(t1); join(t2); join(t3);

            assertEqual(1, successCount.get(), "exactly 1 confirm");
            assertEqual(1, s.report("SKU-B").getFirst().sold(), "sold=1");
        });

        test("per-user limit under contention", () -> {
            InventoryStore s = InventoryStore.load(inv(
                    prod("LIM", "Ltd", 1, 100, 2)));
            CountDownLatch latch = new CountDownLatch(10);
            AtomicInteger successCount = new AtomicInteger();

            Runnable worker = () -> {
                try {
                    s.reserve("same-user", "LIM", 1);
                    successCount.incrementAndGet();
                } catch (InventoryException.PerUserLimit ignored) {
                } finally { latch.countDown(); }
            };

            for (int i = 0; i < 10; i++) Thread.ofPlatform().start(worker);
            await(latch);
            assertTrue(successCount.get() <= 2,
                    "<= 2, got " + successCount.get());
        });
    }

    // ── Lifecycle ────────────────────────────────────────────

    static void testLifecycle() {
        section("Full lifecycle");

        test("full flow", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            StockReport r = s.report("SKU-A").getFirst();
            assertEqual(10, r.available(), "initial avail");
            assertEqual(0, r.reserved(), "initial resvd");
            assertEqual(0, r.sold(), "initial sold");

            Reservation res = s.reserve("alice", "SKU-A", 3);
            r = s.report("SKU-A").getFirst();
            assertEqual(7, r.available(), "after res avail");
            assertEqual(3, r.reserved(), "after res resvd");

            s.reserve("bob", "SKU-A", 2);
            r = s.report("SKU-A").getFirst();
            assertEqual(5, r.available(), "avail");
            assertEqual(5, r.reserved(), "resvd");

            s.confirm(res.reservationId());
            r = s.report("SKU-A").getFirst();
            assertEqual(5, r.available(), "avail");
            assertEqual(2, r.reserved(), "resvd");
            assertEqual(3, r.sold(), "sold");
            assertTrue(r.invariantHolds(), "invariant");
        });

        test("SKU isolation", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A, SKU_B));
            s.reserve("u1", "SKU-A", 5);
            s.reserve("u2", "SKU-A", 3);
            StockReport r = s.report("SKU-B").getFirst();
            assertEqual(5, r.available(), "B avail");
            assertEqual(0, r.reserved(), "B resvd");
            assertEqual(0, r.sold(), "B sold");
        });

        test("never negative", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A)); // max=100, stock=10
            // 999 > stock=10 → OutOfStock should fire first
            assertThrows(InventoryException.OutOfStock.class,
                    () -> s.reserve("u1", "SKU-A", 999), "oversell");
            assertTrue(s.report("SKU-A").getFirst().available() >= 0, "avail >= 0");
        });

        test("invariant always holds", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            for (int i = 0; i < 5; i++) s.reserve("u" + i, "SKU-A", 1);
            Reservation r1 = s.reserve("u-c", "SKU-A", 1);
            s.confirm(r1.reservationId());
            Reservation r2 = s.reserve("u-d", "SKU-A", 1);
            s.cancel(r2.reservationId());
            for (StockReport r : s.reportAll()) {
                assertTrue(r.invariantHolds(),
                        "SKU " + r.sku() + ": " + r.available() + "+" + r.reserved()
                                + "+" + r.sold() + " != " + r.total());
            }
        });

        test("null userId rejected", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            boolean thrown = false;
            try { s.reserve(null, "SKU-A", 1); } catch (NullPointerException e) { thrown = true; }
            assertTrue(thrown, "NPE not thrown for null userId");
        });

        test("null sku rejected", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            boolean thrown = false;
            try { s.reserve("u1", null, 1); } catch (NullPointerException e) { thrown = true; }
            assertTrue(thrown, "NPE not thrown for null sku");
        });

        test("zero TTL rejected", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.InvalidQuantity.class,
                    () -> s.reserve("u1", "SKU-A", 1, 0), "zero ttl");
        });

        test("negative TTL rejected", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            assertThrows(InventoryException.InvalidQuantity.class,
                    () -> s.reserve("u1", "SKU-A", 1, -5), "neg ttl");
        });

        test("SKU index cleaned on expiry", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            Reservation r = s.reserve("u1", "SKU-A", 1, 1);
            sleepMs(1500);
            s.purgeExpired();
            // expiry cleans the SKU index entry — verify by reserving again
            Reservation r2 = s.reserve("u2", "SKU-A", 1);
            assertNotNull(r2, "re-reserve after index cleanup");
            // state should be clean: 10 total, 1 active reserved
            StockReport rep = s.report("SKU-A").getFirst();
            assertEqual(9, rep.available(), "available after re-reserve");
            assertEqual(1, rep.reserved(), "reserved after re-reserve");
            assertEqual(0, rep.sold(), "sold after re-reserve");
        });

        test("large quantity TTL edge", () -> {
            InventoryStore s = InventoryStore.load(inv(SKU_A));
            // Reserve entire stock
            Reservation r = s.reserve("u1", "SKU-A", 10, 1);
            sleepMs(1500);
            // All stock should be back after expiry
            s.purgeExpired();
            StockReport rep = s.report("SKU-A").getFirst();
            assertEqual(10, rep.available(), "all stock available after expiry");
            assertEqual(0, rep.reserved(), "0 reserved");
            // Can reserve full stock again
            s.reserve("u2", "SKU-A", 10);
            assertEqual(0, s.report("SKU-A").getFirst().available(), "fully reserved again");
        });
    }
}