package com.sdsi.inventory.model;

/**
 * Lifecycle: ACTIVE -> CONFIRMED | CANCELLED | EXPIRED. The last three are terminal.
 */
public enum ReservationStatus {
    ACTIVE,
    CONFIRMED,
    CANCELLED,
    EXPIRED;

    public boolean isTerminal() {
        return this != ACTIVE;
    }
}
