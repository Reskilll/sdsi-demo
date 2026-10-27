package com.sdsi.inventory.model;

import java.time.Instant;

/**
 * Immutable snapshot of a reservation, safe to hand to callers and serialise.
 */
public record Reservation(
        String id,
        String sku,
        String userId,
        int quantity,
        Instant createdAt,
        Instant expiresAt,
        ReservationStatus status,
        Instant updatedAt) {
}
