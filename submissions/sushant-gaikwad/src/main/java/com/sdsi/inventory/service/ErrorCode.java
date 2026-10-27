package com.sdsi.inventory.service;

/**
 * Stable, machine-readable error codes. Each maps to one HTTP status in the API layer.
 */
public enum ErrorCode {
    INVALID_INPUT(400),
    UNAUTHORIZED(401),
    SKU_NOT_FOUND(404),
    RESERVATION_NOT_FOUND(404),
    NOT_FOUND(404),
    METHOD_NOT_ALLOWED(405),
    INSUFFICIENT_STOCK(409),
    PER_USER_LIMIT_EXCEEDED(409),
    INVALID_STATE(409),
    IDEMPOTENCY_CONFLICT(409),
    RESERVATION_EXPIRED(410),
    PAYLOAD_TOO_LARGE(413),
    INTERNAL_ERROR(500);

    private final int httpStatus;

    ErrorCode(int httpStatus) {
        this.httpStatus = httpStatus;
    }

    public int httpStatus() {
        return httpStatus;
    }
}
