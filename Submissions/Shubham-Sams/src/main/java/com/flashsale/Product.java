package com.flashsale;

import java.util.Objects;

/**
 * A product in the flash-sale inventory.
 *
 * <p>Stock counters ({@code reserved}, {@code sold}) are guarded by the
 * store lock — all mutation goes through {@link InventoryStore}'s
 * {@code synchronized} blocks.  Plain {@code int} is simpler and correct
 * given the lock discipline.
 */
public class Product {

    private final String sku;
    private final String name;
    private final String description;
    private final double price;
    private final int stock;             // total initially loaded
    private final int maxPerUser;        // per-SKU per-user purchase limit
    private int reserved;
    private int sold;

    public Product(String sku, String name, String description,
                  double price, int stock, int maxPerUser) {
        this.sku = Objects.requireNonNull(sku, "sku must not be null");
        this.name = Objects.requireNonNull(name, "name must not be null");
        this.description = description != null ? description : "";
        this.price = price;
        this.stock = stock;
        this.maxPerUser = maxPerUser;
    }

    /** How many units are available for new reservations right now. */
    public int available() {
        return stock - reserved - sold;
    }

    // ── package-private mutators (only InventoryStore may call, always under synchronized) ──

    void addReserved(int qty) { reserved += qty; }
    void subtractReserved(int qty) { reserved -= qty; }
    void addSold(int qty) { sold += qty; }

    // ── getters ──

    public String sku() { return sku; }
    public String name() { return name; }
    public String description() { return description; }
    public double price() { return price; }
    public int stock() { return stock; }
    public int maxPerUser() { return maxPerUser; }
    public int reserved() { return reserved; }
    public int sold() { return sold; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Product product)) return false;
        return sku.equals(product.sku);
    }

    @Override
    public int hashCode() {
        return sku.hashCode();
    }

    @Override
    public String toString() {
        return "Product[sku=" + sku + ", name=" + name
                + ", stock=" + stock + ", avail=" + available()
                + ", resvd=" + reserved + ", sold=" + sold
                + ", max/user=" + maxPerUser + "]";
    }
}