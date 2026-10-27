package com.flashsale.cli;

import com.flashsale.InventoryException;
import com.flashsale.InventoryStore;
import com.flashsale.Reservation;
import com.flashsale.StockReport;

import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;

/**
 * CLI for the Flash Sale Inventory Reservation System.
 *
 * <h3>Commands</h3>
 * <pre>
 *   reserve &lt;user&gt; &lt;sku&gt; &lt;qty&gt; [--ttl N]
 *   confirm  &lt;reservation-id&gt;
 *   cancel   &lt;reservation-id&gt;
 *   report   [sku]
 *   status   &lt;reservation-id&gt;
 *   purge
 *   demo
 * </pre>
 */
public final class ReservationCli {

    private static final Path DEFAULT_INVENTORY = Path.of("inventory.json");

    private ReservationCli() { /* utility */ }

    public static void main(String[] args) {
        if (args.length == 0) {
            printUsage();
            System.exit(1);
        }

        Path inventory = DEFAULT_INVENTORY;
        int defaultTtl = 120;
        int argIdx = 0;

        // Parse global options
        while (argIdx < args.length && args[argIdx].startsWith("--")) {
            switch (args[argIdx]) {
                case "--inventory", "-i" -> inventory = Path.of(args[++argIdx]);
                case "--ttl" -> defaultTtl = parseIntArg(args[++argIdx], "--ttl");
                default -> {
                    System.err.println("Unknown option: " + args[argIdx]);
                    System.exit(1);
                }
            }
            argIdx++;
        }

        if (argIdx >= args.length) {
            printUsage();
            System.exit(1);
        }

        String command = args[argIdx];
        String[] cmdArgs = Arrays.copyOfRange(args, argIdx + 1, args.length);

        try {
            switch (command) {
                case "reserve" -> cmdReserve(inventory, cmdArgs, defaultTtl);
                case "confirm"  -> cmdConfirm(inventory, cmdArgs, defaultTtl);
                case "cancel"   -> cmdCancel(inventory, cmdArgs, defaultTtl);
                case "report"   -> cmdReport(inventory, cmdArgs, defaultTtl);
                case "status"   -> cmdStatus(inventory, cmdArgs, defaultTtl);
                case "purge"    -> cmdPurge(inventory, defaultTtl);
                case "demo"     -> cmdDemo(inventory, defaultTtl);
                default -> {
                    System.err.println("Unknown command: " + command);
                    printUsage();
                    System.exit(1);
                }
            }
        } catch (InventoryException e) {
            System.err.println("ERROR: " + e.getMessage());
            System.exit(1);
        }
    }

    private static int parseIntArg(String s, String label) {
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            System.err.println("ERROR: " + label + " must be an integer, got: " + s);
            System.exit(1);
            return 0; // unreachable
        }
    }

    // ── command handlers ──

    static void cmdReserve(Path inventory, String[] args, int defaultTtl) {
        if (args.length < 3) { System.err.println("Usage: reserve <user> <sku> <qty> [--ttl N]"); System.exit(1); }
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        String userId = args[0], sku = args[1];
        int qty = parseIntArg(args[2], "quantity");
        Integer ttlOverride = null;
        if (args.length > 3 && args[3].equals("--ttl")) {
            ttlOverride = parseIntArg(args[4], "--ttl");
        }
        Reservation r = store.reserve(userId, sku, qty, ttlOverride);
        System.out.printf("RESERVED  %s  user=%s  sku=%s  qty=%d  ttl=%ds  expires_at=%s%n",
                r.reservationId(), r.userId(), r.sku(), r.quantity(), r.ttlSeconds(), r.expiresAt());
    }

    static void cmdConfirm(Path inventory, String[] args, int defaultTtl) {
        if (args.length < 1) { System.err.println("Usage: confirm <reservation-id>"); System.exit(1); }
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        store.confirm(args[0]);
        Reservation r = store.getReservation(args[0]);
        System.out.printf("CONFIRMED  %s  sku=%s  qty=%d%n", args[0], r.sku(), r.quantity());
    }

    static void cmdCancel(Path inventory, String[] args, int defaultTtl) {
        if (args.length < 1) { System.err.println("Usage: cancel <reservation-id>"); System.exit(1); }
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        store.cancel(args[0]);
        Reservation r = store.getReservation(args[0]);
        System.out.printf("CANCELLED  %s  sku=%s  qty=%d%n", args[0], r.sku(), r.quantity());
    }

    static void cmdReport(Path inventory, String[] args, int defaultTtl) {
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        String sku = args.length > 0 ? args[0] : null;
        List<StockReport> reports = store.report(sku);
        String fmt = "%-20s %-28s %6s %6s %6s %6s%n";
        System.out.printf(fmt, "SKU", "Name", "Total", "Avail", "Resvd", "Sold");
        System.out.println("-".repeat(80));
        for (StockReport r : reports) {
            System.out.printf(fmt, r.sku(), r.name(), r.total(), r.available(), r.reserved(), r.sold());
        }
    }

    static void cmdStatus(Path inventory, String[] args, int defaultTtl) {
        if (args.length < 1) { System.err.println("Usage: status <reservation-id>"); System.exit(1); }
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        Reservation r = store.getReservation(args[0]);
        if (r == null) {
            System.err.println("ERROR: Reservation '" + args[0] + "' not found");
            System.exit(1);
        }
        System.out.println("ID:        " + r.reservationId());
        System.out.println("SKU:       " + r.sku());
        System.out.println("User:      " + r.userId());
        System.out.println("Quantity:  " + r.quantity());
        System.out.println("Status:    " + r.status().name().toLowerCase());
        System.out.println("TTL:       " + r.ttlSeconds() + "s");
        System.out.println("Remaining: " + r.remainingSeconds() + "s");
    }

    static void cmdPurge(Path inventory, int defaultTtl) {
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        int count = store.purgeExpired();
        System.out.println("PURGED  " + count + " expired reservation(s)");
    }

    static void cmdDemo(Path inventory, int defaultTtl) {
        InventoryStore store = InventoryStore.load(inventory, defaultTtl);
        System.out.println("=".repeat(62));
        System.out.println("  FLASH SALE INVENTORY RESERVATION SYSTEM — DEMO");
        System.out.println("=".repeat(62));

        System.out.println("\n📦  INITIAL STOCK");
        System.out.println("-".repeat(62));
        for (StockReport r : store.reportAll()) {
            System.out.printf("  %-20s total=%-4d  available=%-4d%n", r.sku(), r.total(), r.available());
        }

        System.out.println("\n🔒  RESERVE: alice reserves 2 SHOE-RED-42");
        Reservation r1 = store.reserve("alice", "SHOE-RED-42", 2);
        System.out.println("  → " + r1.reservationId() + "  ttl=" + r1.ttlSeconds() + "s");
        printOne(store, "SHOE-RED-42");

        System.out.println("\n🔒  RESERVE: bob reserves 1 WATCH-PRO-ONE");
        Reservation r2 = store.reserve("bob", "WATCH-PRO-ONE", 1);
        System.out.println("  → " + r2.reservationId());
        printOne(store, "WATCH-PRO-ONE");

        System.out.println("\n✅  CONFIRM: alice confirms her reservation");
        store.confirm(r1.reservationId());
        printOne(store, "SHOE-RED-42");

        System.out.println("\n❌  CANCEL: bob cancels his reservation");
        store.cancel(r2.reservationId());
        printOne(store, "WATCH-PRO-ONE");

        System.out.println("\n🛡️  LIMIT CHECK: alice tries to reserve 1 more SHOE-RED-42 (limit=2, already bought 2)");
        try {
            store.reserve("alice", "SHOE-RED-42", 1);
        } catch (InventoryException.PerUserLimit e) {
            System.out.println("  🚫 Blocked: " + e.getMessage());
        }

        System.out.println("\n📉  OUT-OF-STOCK CHECK: alice tries to reserve 1000 BAG-TRAV-01");
        try {
            store.reserve("alice", "BAG-TRAV-01", 1000);
        } catch (InventoryException.OutOfStock e) {
            System.out.println("  🚫 Blocked: " + e.getMessage());
        }

        System.out.println("\n⏳  TTL EXPIRY: charlie reserves 1 PHONE-CASE-X with 2s TTL");
        Reservation r3 = store.reserve("charlie", "PHONE-CASE-X", 1, 2);
        printOne(store, "PHONE-CASE-X");
        System.out.println("  … waiting 3 seconds for TTL to expire …");
        try { Thread.sleep(3000); } catch (InterruptedException ignored) {}
        store.purgeExpired();
        printOne(store, "PHONE-CASE-X");
        System.out.println("  " + r3.reservationId() + " status → " + store.getReservation(r3.reservationId()).status().name().toLowerCase());

        System.out.println("\n📊  FINAL STOCK REPORT");
        System.out.println("-".repeat(62));
        for (StockReport r : store.reportAll()) {
            System.out.printf("  %-20s total=%-4d  available=%-4d  reserved=%-4d  sold=%-4d%n",
                    r.sku(), r.total(), r.available(), r.reserved(), r.sold());
        }

        System.out.println("\n✅  Demo complete.");
    }

    private static void printOne(InventoryStore store, String sku) {
        StockReport r = store.report(sku).getFirst();
        System.out.printf("  → %s: avail=%d  reserved=%d  sold=%d%n", r.sku(), r.available(), r.reserved(), r.sold());
    }

    private static void printUsage() {
        System.out.println("""
                Inventory Reservation System — Flash Sale Engine

                Usage:
                  reserve  <user> <sku> <qty> [--ttl N]   Reserve stock
                  confirm  <reservation-id>               Confirm purchase
                  cancel   <reservation-id>               Cancel reservation
                  report   [sku]                          Show stock report
                  status   <reservation-id>               Show reservation
                  purge                                   Expire timed-out holds
                  demo                                    Run demo

                Options:
                  --inventory, -i <path>  Path to inventory.json (default: ./inventory.json)
                  --ttl <seconds>         Default TTL (default: 120)
                """);
    }
}