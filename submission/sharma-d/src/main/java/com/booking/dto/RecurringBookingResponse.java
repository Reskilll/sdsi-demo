package com.booking.dto;

import com.booking.model.Booking;
import com.booking.model.RecurringBooking;
import java.util.List;

public class RecurringBookingResponse {
    private RecurringBooking recurrence;
    private List<Booking> successful;
    private List<ConflictDetail> conflicts;

    public RecurringBookingResponse() {}

    public RecurringBookingResponse(RecurringBooking recurrence, List<Booking> successful,
                                    List<ConflictDetail> conflicts) {
        this.recurrence = recurrence;
        this.successful = successful;
        this.conflicts = conflicts;
    }

    public RecurringBooking getRecurrence() { return recurrence; }
    public void setRecurrence(RecurringBooking recurrence) { this.recurrence = recurrence; }

    public List<Booking> getSuccessful() { return successful; }
    public void setSuccessful(List<Booking> successful) { this.successful = successful; }

    public List<ConflictDetail> getConflicts() { return conflicts; }
    public void setConflicts(List<ConflictDetail> conflicts) { this.conflicts = conflicts; }

    public static class ConflictDetail {
        private String date;
        private String reason;

        public ConflictDetail() {}

        public ConflictDetail(String date, String reason) {
            this.date = date;
            this.reason = reason;
        }

        public String getDate() { return date; }
        public void setDate(String date) { this.date = date; }

        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
    }
}