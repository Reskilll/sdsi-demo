package com.flashsale;

/**
 * Read-only snapshot of stock counts for a single SKU.
 *
 * <p>Invariant: {@code available + reserved + sold == total}.
 */
public record StockReport(
        String sku,
        String name,
        int total,
        int available,
        int reserved,
        int sold) {

    public boolean invariantHolds() {
        return available + reserved + sold == total;
    }
}