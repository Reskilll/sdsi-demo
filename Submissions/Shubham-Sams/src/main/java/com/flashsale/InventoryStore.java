package com.flashsale;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Thread-safe inventory store for flash sales.
 *
 * <h3>Design</h3>
 * <p>All mutation is synchronized on the store's intrinsic lock.  This is
 * deliberately coarse-grained — flash-sale workloads are write-contention-heavy,
 * and fine-grained per-SKU locks add deadlock risk with negligible throughput
 * benefit in a Java monitor (which already biases toward the owning thread).
 *
 * <h3>TTL expiry</h3>
 * Expired reservations are cleaned <em>lazily</em> when any operation touches
 * the product or reservation — no background thread.  Call
 * {@link #purgeExpired()} to sweep the entire store explicitly.
 *
 * <h3>Usage</h3>
 * <pre>{@code
 *   InventoryStore store = InventoryStore.load(Path.of("inventory.json"));
 *   Reservation r = store.reserve("alice", "SHOE-RED-42", 2);
 *   store.confirm(r.reservationId());
 *   // or: store.cancel(r.reservationId());
 *   List<StockReport> reports = store.report(null);
 * }</pre>
 */
public class InventoryStore {

    private final Map<String, Product> products;
    private final Map<String, Reservation> reservations;
    private final int defaultTtlSeconds;

    /** Per-user confirmed-purchase count: key = "userId::sku" */
    private final Map<String, Integer> userPurchases;

    /**
     * Secondary index: sku → reservationIds.
     * Maintained on every reservation insert so that lookup/purge are O(1)
     * per SKU rather than O(n) full-map scans during flash-sale peaks.
     */
    private final Map<String, Set<String>> reservationIdsBySku;

    private InventoryStore(Map<String, Product> products, int defaultTtlSeconds) {
        this.products = new HashMap<>(products);
        this.reservations = new HashMap<>();
        this.defaultTtlSeconds = defaultTtlSeconds;
        this.userPurchases = new HashMap<>();
        this.reservationIdsBySku = new HashMap<>();
    }

    // ──────────────────────────────────────────────────────────
    // Factory
    // ──────────────────────────────────────────────────────────

    /**
     * Load products from a JSON file using the built-in lightweight parser.
     *
     * <pre>{
     *   "products": [
     *     { "sku": "A", "name": "...", "price": 99, "stock": 10, "max_per_user": 2 }
     *   ]
     * }</pre>
     *
     * @param path  path to the inventory JSON file
     * @param ttl   default reservation TTL in seconds
     * @throws InventoryException if the file is missing, malformed, or contains invalid data
     */
    @SuppressWarnings("unchecked")
    public static InventoryStore load(Path path, int ttl) {
        String text;
        try {
            text = Files.readString(path);
        } catch (IOException e) {
            throw new InventoryException("Cannot read inventory file: " + path, e);
        }

        Map<String, Object> root;
        try {
            root = Json.parseObject(text);
        } catch (RuntimeException e) {
            throw new InventoryException("Invalid JSON in " + path + ": " + e.getMessage(), e);
        }

        Object productsObj = root.get("products");
        if (!(productsObj instanceof List<?> list) || list.isEmpty()) {
            throw new InventoryException("No products found in " + path);
        }

        Map<String, Product> productMap = new LinkedHashMap<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> m)) {
                throw new InventoryException("Invalid product entry in " + path + ": " + item);
            }
            Product p = parseProduct((Map<String, Object>) m, path.toString());
            if (productMap.containsKey(p.sku())) {
                throw new InventoryException("Duplicate SKU '" + p.sku() + "' in " + path);
            }
            productMap.put(p.sku(), p);
        }

        return new InventoryStore(productMap, ttl);
    }

    /** Convenience overload with default TTL of 120 s. */
    public static InventoryStore load(Path path) {
        return load(path, 120);
    }

    private static Product parseProduct(Map<String, Object> item, String source) {
        try {
            String sku = requireString(item, "sku");
            String name = requireString(item, "name");
            String description = Objects.toString(item.getOrDefault("description", ""), "");
            double price = ((Number) requireField(item, "price")).doubleValue();
            int stock = ((Number) requireField(item, "stock")).intValue();
            int maxPerUser = ((Number) requireField(item, "max_per_user")).intValue();

            if (stock < 0)
                throw new InventoryException("Negative stock for SKU '" + sku + "': " + stock);
            if (price < 0)
                throw new InventoryException("Negative price for SKU '" + sku + "': " + price);
            if (maxPerUser < 1)
                throw new InventoryException("max_per_user must be >= 1 for SKU '" + sku + "': " + maxPerUser);

            return new Product(sku, name, description, price, stock, maxPerUser);
        } catch (ClassCastException | NullPointerException e) {
            throw new InventoryException("Invalid product entry in " + source + ": " + item, e);
        }
    }

    private static String requireString(Map<String, Object> map, String key) {
        return Objects.toString(requireField(map, key), "");
    }

    private static Object requireField(Map<String, Object> map, String key) {
        Object val = map.get(key);
        if (val == null)
            throw new InventoryException("Missing field '" + key + "'");
        return val;
    }

    // ──────────────────────────────────────────────────────────
    // Public API — Reserve / Confirm / Cancel
    // ──────────────────────────────────────────────────────────

    /**
     * Reserve {@code quantity} of {@code sku} for {@code userId}.
     *
     * <p>The reservation is held for {@code ttlOverride} seconds (or the
     * store default).
     *
     * @return a new active {@link Reservation}
     * @throws InventoryException.OutOfStock       not enough available stock
     * @throws InventoryException.PerUserLimit     user would exceed their per-SKU limit
     * @throws InventoryException.InvalidQuantity  quantity &lt;= 0
     * @throws InventoryException                  unknown SKU
     */
    public synchronized Reservation reserve(String userId, String sku, int quantity, Integer ttlOverride) {
        Objects.requireNonNull(userId, "userId must not be null");
        Objects.requireNonNull(sku, "sku must not be null");
        if (quantity <= 0) {
            throw new InventoryException.InvalidQuantity("quantity must be >= 1, got " + quantity);
        }
        int ttl = ttlOverride != null ? ttlOverride : defaultTtlSeconds;
        if (ttl <= 0) {
            throw new InventoryException.InvalidQuantity("TTL must be >= 1, got " + ttl);
        }
        Product product = getProduct(sku);
        purgeExpiredForProduct(product);

        if (quantity > product.available()) {
            throw new InventoryException.OutOfStock(
                    "SKU '" + sku + "': requested " + quantity + ", available " + product.available());
        }

        int held = userHeldCount(userId, sku);
        if (held + quantity > product.maxPerUser()) {
            throw new InventoryException.PerUserLimit(
                    "User '" + userId + "' already holds " + held + " of SKU '" + sku
                            + "' (max " + product.maxPerUser() + "). Cannot reserve " + quantity + " more.");
        }

        product.addReserved(quantity);
        Reservation r = new Reservation(sku, userId, quantity, ttl);
        reservations.put(r.reservationId(), r);
        reservationIdsBySku.computeIfAbsent(sku, k -> new HashSet<>())
                .add(r.reservationId());
        return r;
    }

    /** Convenience overload using the store default TTL. */
    public Reservation reserve(String userId, String sku, int quantity) {
        return reserve(userId, sku, quantity, null);
    }

    /**
     * Permanently deduct stock for an active reservation.
     *
     * @throws InventoryException.ReservationNotFound if the ID is unknown or not ACTIVE
     */
    public synchronized void confirm(String reservationId) {
        Reservation r = requireActiveReservation(reservationId);
        Product product = getProduct(r.sku());
        product.subtractReserved(r.quantity());
        product.addSold(r.quantity());
        r.markConfirmed();

        String key = r.userId() + "::" + r.sku();
        userPurchases.merge(key, r.quantity(), Integer::sum);
    }

    /**
     * Release an active reservation back into available stock.
     *
     * @throws InventoryException.ReservationNotFound if the ID is unknown or not ACTIVE
     */
    public synchronized void cancel(String reservationId) {
        Reservation r = requireActiveReservation(reservationId);
        Product product = getProduct(r.sku());
        product.subtractReserved(r.quantity());
        r.markCancelled();
    }

    /**
     * Validates that a reservation exists, is ACTIVE, and has not expired.
     * If expired, releases stock and throws ReservationNotFound.
     */
    private Reservation requireActiveReservation(String reservationId) {
        Reservation r = reservations.get(reservationId);
        if (r == null) {
            throw new InventoryException.ReservationNotFound(
                    "Reservation '" + reservationId + "' not found");
        }
        if (r.isExpired()) {
            expireReservation(r);
            throw new InventoryException.ReservationNotFound(
                    "Reservation '" + reservationId + "' has expired");
        }
        if (r.status() != ReservationStatus.ACTIVE) {
            throw new InventoryException.ReservationNotFound(
                    "Reservation '" + reservationId + "' is " + r.status().name().toLowerCase());
        }
        return r;
    }

    // ──────────────────────────────────────────────────────────
    // Public API — Query
    // ──────────────────────────────────────────────────────────

    /** Look up a reservation by ID. Returns {@code null} if not found. */
    public synchronized Reservation getReservation(String reservationId) {
        Reservation r = reservations.get(reservationId);
        if (r == null) return null;
        if (r.status() == ReservationStatus.ACTIVE && r.isExpired()) {
            expireReservation(r);
        }
        return r;
    }

    /**
     * Return a stock report for {@code sku}, or all products if {@code sku}
     * is {@code null}.  Expired reservations are purged before computing.
     */
    public synchronized List<StockReport> report(String sku) {
        purgeAllExpired();
        if (sku != null) {
            Product p = getProduct(sku);
            return List.of(toReport(p));
        }
        return products.values().stream()
                .map(this::toReport)
                .toList();
    }

    /** Report on all products (convenience). */
    public List<StockReport> reportAll() {
        return report(null);
    }

    /**
     * Expire all timed-out reservations.  Returns the count expired.
     */
    public synchronized int purgeExpired() {
        return purgeAllExpired();
    }

    // ──────────────────────────────────────────────────────────
    // Internals — always called under synchronized
    // ──────────────────────────────────────────────────────────

    private Product getProduct(String sku) {
        Product p = products.get(sku);
        if (p == null) throw new InventoryException("Unknown SKU: '" + sku + "'");
        return p;
    }

    private int userHeldCount(String userId, String sku) {
        int confirmed = userPurchases.getOrDefault(userId + "::" + sku, 0);
        int active = 0;
        Set<String> ids = reservationIdsBySku.get(sku);
        if (ids != null) {
            for (String id : ids) {
                Reservation r = reservations.get(id);
                if (r != null
                        && r.userId().equals(userId)
                        && r.status() == ReservationStatus.ACTIVE
                        && !r.isExpired()) {
                    active += r.quantity();
                }
            }
        }
        return confirmed + active;
    }

    private void purgeExpiredForProduct(Product product) {
        Set<String> ids = reservationIdsBySku.get(product.sku());
        if (ids == null) return;
        for (Iterator<String> it = ids.iterator(); it.hasNext(); ) {
            Reservation r = reservations.get(it.next());
            if (r != null && r.status() == ReservationStatus.ACTIVE && r.isExpired()) {
                expireReservation(r);
            }
        }
    }

    private int purgeAllExpired() {
        int count = 0;
        for (Iterator<Map.Entry<String, Reservation>> it = reservations.entrySet().iterator(); it.hasNext(); ) {
            Reservation r = it.next().getValue();
            if (r.status() == ReservationStatus.ACTIVE && r.isExpired()) {
                expireReservation(r);
                count++;
            }
        }
        return count;
    }

    /** Also clean up the SKU index entry when purging. */
    private void expireReservation(Reservation r) {
        Product product = products.get(r.sku());
        if (product != null) {
            product.subtractReserved(r.quantity());
        }
        r.markExpired();
        // Remove from SKU index — the reservation won't be referenced again
        Set<String> ids = reservationIdsBySku.get(r.sku());
        if (ids != null) {
            ids.remove(r.reservationId());
            if (ids.isEmpty()) reservationIdsBySku.remove(r.sku());
        }
    }

    private StockReport toReport(Product p) {
        return new StockReport(p.sku(), p.name(), p.stock(),
                p.available(), p.reserved(), p.sold());
    }
}