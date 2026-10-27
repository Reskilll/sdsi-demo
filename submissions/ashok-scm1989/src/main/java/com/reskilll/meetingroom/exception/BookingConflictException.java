package com.reskilll.meetingroom.exception;

public class BookingConflictException extends RuntimeException {
    private final String conflictingBookingId;
    private final String conflictingOrganiser;

    public BookingConflictException(String message) {
        super(message);
        this.conflictingBookingId = null;
        this.conflictingOrganiser = null;
    }

    public BookingConflictException(String message, String conflictingBookingId, String conflictingOrganiser) {
        super(message);
        this.conflictingBookingId = conflictingBookingId;
        this.conflictingOrganiser = conflictingOrganiser;
    }

    public String getConflictingBookingId() {
        return conflictingBookingId;
    }

    public String getConflictingOrganiser() {
        return conflictingOrganiser;
    }
}
