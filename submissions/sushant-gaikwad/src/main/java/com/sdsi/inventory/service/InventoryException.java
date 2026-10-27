package com.sdsi.inventory.service;

/**
 * Domain error with a stable {@link ErrorCode}. Messages never include internal state beyond the request.
 */
public class InventoryException extends RuntimeException {

    private final ErrorCode code;

    public InventoryException(ErrorCode code, String message) {
        super(message);
        this.code = code;
    }

    public ErrorCode code() {
        return code;
    }
}
