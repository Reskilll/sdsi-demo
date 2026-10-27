package com.flashsale;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * A time-limited stock hold for a user.
 *
 * <p>A reservation is created via {@link InventoryStore#reserve} and must be
 * {@link #confirm() confirmed} or {@link #cancel() cancelled} before its TTL
 * expires.  Expired reservations release their stock back into the available
 * pool.
 */
public class Reservation {

    private final String reservationId;
    private final String sku;
    private final String userId;
    private final int quantity;
    private final Instant createdAt;
    private final int ttlSeconds;
    private volatile ReservationStatus status;

    Reservation(String sku, String userId, int quantity, int ttlSeconds) {
        this.reservationId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        this.sku = Objects.requireNonNull(sku);
        this.userId = Objects.requireNonNull(userId);
        this.quantity = quantity;
        this.createdAt = Instant.now();
        this.ttlSeconds = ttlSeconds;
        this.status = ReservationStatus.ACTIVE;
    }

    /** The instant at which this reservation expires. */
    public Instant expiresAt() {
        return createdAt.plusSeconds(ttlSeconds);
    }

    /** True if the reservation is still ACTIVE but past its TTL. */
    public boolean isExpired() {
        return status == ReservationStatus.ACTIVE
                && Instant.now().isAfter(expiresAt());
    }

    /** Seconds remaining before expiry (0 if expired). */
    public long remainingSeconds() {
        long sec = expiresAt().getEpochSecond() - Instant.now().getEpochSecond();
        return Math.max(0, sec);
    }

    // ── package-private lifecycle (only InventoryStore may transition) ──

    void markConfirmed() { this.status = ReservationStatus.CONFIRMED; }
    void markCancelled() { this.status = ReservationStatus.CANCELLED; }
    void markExpired()  { this.status = ReservationStatus.EXPIRED; }

    // ── getters ──

    public String reservationId() { return reservationId; }
    public String sku() { return sku; }
    public String userId() { return userId; }
    public int quantity() { return quantity; }
    public Instant createdAt() { return createdAt; }
    public int ttlSeconds() { return ttlSeconds; }
    public ReservationStatus status() { return status; }

    @Override
    public String toString() {
        return "Reservation[id=" + reservationId + ", sku=" + sku
                + ", user=" + userId + ", qty=" + quantity
                + ", status=" + status + ", ttl=" + ttlSeconds + "s"
                + ", remaining=" + remainingSeconds() + "s]";
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Reservation that)) return false;
        return reservationId.equals(that.reservationId);
    }

    @Override
    public int hashCode() {
        return reservationId.hashCode();
    }
}