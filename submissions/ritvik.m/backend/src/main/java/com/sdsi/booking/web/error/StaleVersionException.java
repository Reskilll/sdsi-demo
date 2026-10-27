package com.sdsi.booking.web.error;

import org.springframework.http.HttpStatus;

public class StaleVersionException extends ApiException {

    public StaleVersionException(long supplied, long current) {
        super(HttpStatus.CONFLICT, "STALE_VERSION",
                "The booking was modified by someone else (supplied version " + supplied
                        + ", current version " + current + "). Reload and try again.");
    }
}
