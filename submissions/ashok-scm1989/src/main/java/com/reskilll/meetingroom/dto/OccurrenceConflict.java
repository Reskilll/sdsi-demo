package com.reskilll.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.LocalDate;
import java.time.LocalDateTime;

public class OccurrenceConflict {

    private int occurrenceIndex;

    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate date;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime startTime;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime endTime;

    private String reason;
    private String message;
    private String conflictingBookingId;
    private String conflictingOrganiser;

    public OccurrenceConflict() {
    }

    public OccurrenceConflict(int occurrenceIndex, LocalDate date,
                              LocalDateTime startTime, LocalDateTime endTime,
                              String reason, String message,
                              String conflictingBookingId, String conflictingOrganiser) {
        this.occurrenceIndex = occurrenceIndex;
        this.date = date;
        this.startTime = startTime;
        this.endTime = endTime;
        this.reason = reason;
        this.message = message;
        this.conflictingBookingId = conflictingBookingId;
        this.conflictingOrganiser = conflictingOrganiser;
    }

    public int getOccurrenceIndex() {
        return occurrenceIndex;
    }

    public void setOccurrenceIndex(int occurrenceIndex) {
        this.occurrenceIndex = occurrenceIndex;
    }

    public LocalDate getDate() {
        return date;
    }

    public void setDate(LocalDate date) {
        this.date = date;
    }

    public LocalDateTime getStartTime() {
        return startTime;
    }

    public void setStartTime(LocalDateTime startTime) {
        this.startTime = startTime;
    }

    public LocalDateTime getEndTime() {
        return endTime;
    }

    public void setEndTime(LocalDateTime endTime) {
        this.endTime = endTime;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getConflictingBookingId() {
        return conflictingBookingId;
    }

    public void setConflictingBookingId(String conflictingBookingId) {
        this.conflictingBookingId = conflictingBookingId;
    }

    public String getConflictingOrganiser() {
        return conflictingOrganiser;
    }

    public void setConflictingOrganiser(String conflictingOrganiser) {
        this.conflictingOrganiser = conflictingOrganiser;
    }
}
