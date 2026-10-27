package com.sdsi.booking.web.error;

import org.springframework.http.HttpStatus;

import java.util.List;

/** Domain failure carrying the HTTP status the REST layer must surface. */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final List<String> details;

    public ApiException(HttpStatus status, String message) {
        this(status, message, List.of());
    }

    public ApiException(HttpStatus status, String message, List<String> details) {
        super(message);
        this.status = status;
        this.details = List.copyOf(details);
    }

    public HttpStatus getStatus() {
        return status;
    }

    public List<String> getDetails() {
        return details;
    }

    /** 400 — malformed request: bad window, outside operating hours, unknown room. */
    public static class BadRequest extends ApiException {
        public BadRequest(String message) {
            super(HttpStatus.BAD_REQUEST, message);
        }

        public BadRequest(String message, List<String> details) {
            super(HttpStatus.BAD_REQUEST, message, details);
        }
    }

    /** 400 — M3: {@code attendees.size() > room.capacity}. */
    public static class CapacityExceeded extends ApiException {
        public CapacityExceeded(String message) {
            super(HttpStatus.BAD_REQUEST, message);
        }
    }

    /** 404 — unknown room or booking. */
    public static class NotFound extends ApiException {
        public NotFound(String message) {
            super(HttpStatus.NOT_FOUND, message);
        }
    }

    /** 409 — M2: the room is already occupied during the requested window. */
    public static class Conflict extends ApiException {
        public Conflict(String message) {
            super(HttpStatus.CONFLICT, message);
        }

        public Conflict(String message, List<String> details) {
            super(HttpStatus.CONFLICT, message, details);
        }
    }
}
