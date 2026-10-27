package com.reskilll.meetingroom.dto;

import com.reskilll.meetingroom.model.RecurrencePolicy;
import java.util.ArrayList;
import java.util.List;

public class RecurringBookingResult {

    private String recurrenceGroupId;
    private RecurrencePolicy policy;
    private int totalRequested;
    private int successfulCount;
    private int conflictCount;
    private List<BookingResponse> successfulBookings = new ArrayList<>();
    private List<OccurrenceConflict> conflicts = new ArrayList<>();

    public RecurringBookingResult() {
    }

    public RecurringBookingResult(String recurrenceGroupId, RecurrencePolicy policy,
                                  int totalRequested, int successfulCount, int conflictCount,
                                  List<BookingResponse> successfulBookings,
                                  List<OccurrenceConflict> conflicts) {
        this.recurrenceGroupId = recurrenceGroupId;
        this.policy = policy;
        this.totalRequested = totalRequested;
        this.successfulCount = successfulCount;
        this.conflictCount = conflictCount;
        if (successfulBookings != null) {
            this.successfulBookings = successfulBookings;
        }
        if (conflicts != null) {
            this.conflicts = conflicts;
        }
    }

    public String getRecurrenceGroupId() {
        return recurrenceGroupId;
    }

    public void setRecurrenceGroupId(String recurrenceGroupId) {
        this.recurrenceGroupId = recurrenceGroupId;
    }

    public RecurrencePolicy getPolicy() {
        return policy;
    }

    public void setPolicy(RecurrencePolicy policy) {
        this.policy = policy;
    }

    public int getTotalRequested() {
        return totalRequested;
    }

    public void setTotalRequested(int totalRequested) {
        this.totalRequested = totalRequested;
    }

    public int getSuccessfulCount() {
        return successfulCount;
    }

    public void setSuccessfulCount(int successfulCount) {
        this.successfulCount = successfulCount;
    }

    public int getConflictCount() {
        return conflictCount;
    }

    public void setConflictCount(int conflictCount) {
        this.conflictCount = conflictCount;
    }

    public List<BookingResponse> getSuccessfulBookings() {
        return successfulBookings;
    }

    public void setSuccessfulBookings(List<BookingResponse> successfulBookings) {
        this.successfulBookings = successfulBookings;
    }

    public List<OccurrenceConflict> getConflicts() {
        return conflicts;
    }

    public void setConflicts(List<OccurrenceConflict> conflicts) {
        this.conflicts = conflicts;
    }
}
