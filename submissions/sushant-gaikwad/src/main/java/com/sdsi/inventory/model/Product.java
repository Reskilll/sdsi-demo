package com.sdsi.inventory.model;

/**
 * Immutable catalogue entry loaded from the inventory file.
 *
 * @param sku          unique stock-keeping unit
 * @param name         display name
 * @param stock        initial units available for sale
 * @param perUserLimit max units one user may hold + buy for this SKU
 */
public record Product(String sku, String name, int stock, int perUserLimit) {
}
