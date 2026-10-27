package com.reskilll.meetingroom.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.LocalDateTime;

public class SlotRecommendation {

    private String roomId;
    private String roomName;
    private int roomCapacity;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime startTime;

    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
    private LocalDateTime endTime;

    private int durationMinutes;
    private int attendeeCount;
    private String officeHoursWindow = "09:00 - 18:00";

    public SlotRecommendation() {
    }

    public SlotRecommendation(String roomId, String roomName, int roomCapacity,
                              LocalDateTime startTime, LocalDateTime endTime,
                              int durationMinutes, int attendeeCount) {
        this.roomId = roomId;
        this.roomName = roomName;
        this.roomCapacity = roomCapacity;
        this.startTime = startTime;
        this.endTime = endTime;
        this.durationMinutes = durationMinutes;
        this.attendeeCount = attendeeCount;
    }

    public String getRoomId() {
        return roomId;
    }

    public void setRoomId(String roomId) {
        this.roomId = roomId;
    }

    public String getRoomName() {
        return roomName;
    }

    public void setRoomName(String roomName) {
        this.roomName = roomName;
    }

    public int getRoomCapacity() {
        return roomCapacity;
    }

    public void setRoomCapacity(int roomCapacity) {
        this.roomCapacity = roomCapacity;
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

    public int getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(int durationMinutes) {
        this.durationMinutes = durationMinutes;
    }

    public int getAttendeeCount() {
        return attendeeCount;
    }

    public void setAttendeeCount(int attendeeCount) {
        this.attendeeCount = attendeeCount;
    }

    public String getOfficeHoursWindow() {
        return officeHoursWindow;
    }

    public void setOfficeHoursWindow(String officeHoursWindow) {
        this.officeHoursWindow = officeHoursWindow;
    }
}
