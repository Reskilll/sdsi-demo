package com.booking.dto;

public class FindSlotResponse {
    private boolean found;
    private String roomId;
    private String roomName;
    private String date;
    private String startTime;

    public FindSlotResponse() {}

    public FindSlotResponse(boolean found, String roomId, String roomName, String date, String startTime) {
        this.found = found;
        this.roomId = roomId;
        this.roomName = roomName;
        this.date = date;
        this.startTime = startTime;
    }

    public boolean isFound() { return found; }
    public void setFound(boolean found) { this.found = found; }

    public String getRoomId() { return roomId; }
    public void setRoomId(String roomId) { this.roomId = roomId; }

    public String getRoomName() { return roomName; }
    public void setRoomName(String roomName) { this.roomName = roomName; }

    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }

    public String getStartTime() { return startTime; }
    public void setStartTime(String startTime) { this.startTime = startTime; }
}