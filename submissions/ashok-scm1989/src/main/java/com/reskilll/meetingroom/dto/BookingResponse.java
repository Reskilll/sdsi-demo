package com.reskilll.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.reskilll.meetingroom.model.Booking;
import java.time.LocalDateTime;
import java.util.List;

public class BookingResponse {
    private String id;
    private String roomId;
    private String title;
    private String organiser;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime startTime;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime endTime;

    private List<String> attendees;
    private int attendeeCount;
    private String recurrenceGroupId;
    private Integer occurrenceIndex;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime createdAt;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime updatedAt;

    public BookingResponse() {
    }

    public static BookingResponse fromEntity(Booking entity) {
        BookingResponse dto = new BookingResponse();
        dto.setId(entity.getId());
        dto.setRoomId(entity.getRoomId());
        dto.setTitle(entity.getTitle());
        dto.setOrganiser(entity.getOrganiser());
        dto.setStartTime(entity.getStartTime());
        dto.setEndTime(entity.getEndTime());
        dto.setAttendees(entity.getAttendees());
        dto.setAttendeeCount(entity.getAttendees() != null ? entity.getAttendees().size() : 0);
        dto.setRecurrenceGroupId(entity.getRecurrenceGroupId());
        dto.setOccurrenceIndex(entity.getOccurrenceIndex());
        dto.setCreatedAt(entity.getCreatedAt());
        dto.setUpdatedAt(entity.getUpdatedAt());
        return dto;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
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

    public int getAttendeeCount() {
        return attendeeCount;
    }

    public void setAttendeeCount(int attendeeCount) {
        this.attendeeCount = attendeeCount;
    }

    public String getRecurrenceGroupId() {
        return recurrenceGroupId;
    }

    public void setRecurrenceGroupId(String recurrenceGroupId) {
        this.recurrenceGroupId = recurrenceGroupId;
    }

    public Integer getOccurrenceIndex() {
        return occurrenceIndex;
    }

    public void setOccurrenceIndex(Integer occurrenceIndex) {
        this.occurrenceIndex = occurrenceIndex;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
