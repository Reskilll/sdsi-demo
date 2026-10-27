package com.reskilll.meetingroom.exception;

public class CapacityExceededException extends RuntimeException {
    private final String roomId;
    private final int requestedAttendees;
    private final int roomCapacity;

    public CapacityExceededException(String roomId, int requestedAttendees, int roomCapacity) {
        super(String.format("Room '%s' has capacity %d, but %d attendees were requested",
                roomId, roomCapacity, requestedAttendees));
        this.roomId = roomId;
        this.requestedAttendees = requestedAttendees;
        this.roomCapacity = roomCapacity;
    }

    public String getRoomId() {
        return roomId;
    }

    public int getRequestedAttendees() {
        return requestedAttendees;
    }

    public int getRoomCapacity() {
        return roomCapacity;
    }
}
