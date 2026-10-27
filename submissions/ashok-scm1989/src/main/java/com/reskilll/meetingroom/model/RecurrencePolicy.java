package com.reskilll.meetingroom.model;

public enum RecurrencePolicy {
    /**
     * If any occurrence conflicts, reject all occurrences and persist none.
     */
    ALL_OR_NOTHING,

    /**
     * Persist occurrences that are free, and return details for conflicted ones.
     */
    BOOK_AVAILABLE
}
