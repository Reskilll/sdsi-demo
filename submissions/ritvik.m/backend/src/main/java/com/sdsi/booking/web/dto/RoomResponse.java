package com.sdsi.booking.web.dto;

import java.util.Set;

public record RoomResponse(
        String id,
        String name,
        int capacity,
        Integer floor,
        String location,
        Set<String> amenities) {
}
