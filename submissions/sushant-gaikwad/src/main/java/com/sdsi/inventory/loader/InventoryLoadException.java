package com.sdsi.inventory.loader;

/** Raised when the inventory file is missing, unreadable or fails validation. */
public class InventoryLoadException extends RuntimeException {

    public InventoryLoadException(String message) {
        super(message);
    }

    public InventoryLoadException(String message, Throwable cause) {
        super(message, cause);
    }
}
