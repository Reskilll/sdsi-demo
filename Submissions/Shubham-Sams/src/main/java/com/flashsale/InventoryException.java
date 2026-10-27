package com.flashsale;

/**
 * Base exception for all inventory-related errors.
 *
 * <p>Concrete subclasses allow callers to distinguish between
 * recoverable situations (e.g. out-of-stock) and programmer errors.
 */
public class InventoryException extends RuntimeException {

    public InventoryException(String message) {
        super(message);
    }

    public InventoryException(String message, Throwable cause) {
        super(message, cause);
    }

    // ── concrete error types ──

    /** Not enough available stock to fulfil the reservation. */
    public static class OutOfStock extends InventoryException {
        public OutOfStock(String message) { super(message); }
        public OutOfStock(String message, Throwable cause) { super(message, cause); }
    }

    /** User would exceed their per-SKU purchase limit. */
    public static class PerUserLimit extends InventoryException {
        public PerUserLimit(String message) { super(message); }
        public PerUserLimit(String message, Throwable cause) { super(message, cause); }
    }

    /** Reservation ID is unknown, already confirmed, cancelled, or expired. */
    public static class ReservationNotFound extends InventoryException {
        public ReservationNotFound(String message) { super(message); }
        public ReservationNotFound(String message, Throwable cause) { super(message, cause); }
    }

    /** Quantity must be a positive integer. */
    public static class InvalidQuantity extends InventoryException {
        public InvalidQuantity(String message) { super(message); }
        public InvalidQuantity(String message, Throwable cause) { super(message, cause); }
    }
}