package com.sdsi.booking.web.error;

import org.springframework.http.HttpStatus;

/**
 * A request that is syntactically valid but breaks a business rule
 * (capacity, opening hours, attendee mismatch, ...).
 */
public class RuleViolationException extends ApiException {

    public RuleViolationException(String code, String message) {
        super(HttpStatus.BAD_REQUEST, code, message);
    }
}
