package com.reskilll.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.reskilll.meetingroom.model.RecurrencePolicy;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.List;

public class RecurringBookingRequest {

    @NotBlank(message = "Room ID is required")
    private String roomId;

    private String title;

    @NotBlank(message = "Organiser is required")
    private String organiser;

    @NotNull(message = "Start time is required")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime startTime;

    @NotNull(message = "End time is required")
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime endTime;

    @NotEmpty(message = "Attendees list cannot be empty")
    private List<String> attendees;

    @Min(value = 1, message = "Occurrences must be at least 1")
    @Max(value = 52, message = "Occurrences cannot exceed 52 weeks")
    private int occurrences = 4;

    private RecurrencePolicy policy = RecurrencePolicy.BOOK_AVAILABLE;

    public RecurringBookingRequest() {
    }

    public RecurringBookingRequest(String roomId, String title, String organiser,
                                   LocalDateTime startTime, LocalDateTime endTime,
                                   List<String> attendees, int occurrences,
                                   RecurrencePolicy policy) {
        this.roomId = roomId;
        this.title = title;
        this.organiser = organiser;
        this.startTime = startTime;
        this.endTime = endTime;
        this.attendees = attendees;
        this.occurrences = occurrences;
        this.policy = policy != null ? policy : RecurrencePolicy.BOOK_AVAILABLE;
    }

    public String getRoomId() {
        return roomId;
    }

    public void setRoomId(String roomId) {
        this.roomId = roomId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getOrganiser() {
        return organiser;
    }

    public void setOrganiser(String organiser) {
        this.organiser = organiser;
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

    public List<String> getAttendees() {
        return attendees;
    }

    public void setAttendees(List<String> attendees) {
        this.attendees = attendees;
    }

    public int getOccurrences() {
        return occurrences;
    }

    public void setOccurrences(int occurrences) {
        this.occurrences = occurrences;
    }

    public RecurrencePolicy getPolicy() {
        return policy;
    }

    public void setPolicy(RecurrencePolicy policy) {
        this.policy = policy;
    }
}
