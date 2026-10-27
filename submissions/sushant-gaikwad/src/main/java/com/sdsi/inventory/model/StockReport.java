package com.sdsi.inventory.model;

/**
 * Point-in-time counts for one SKU. Invariant: available + reserved + sold == total.
 */
public record StockReport(String sku, String name, int total, int available, int reserved, int sold, int perUserLimit) {
}
