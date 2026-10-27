package com.booking.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record Room(
        @JsonProperty(required = true) String id,
        @JsonProperty(required = true) String name,
        @JsonProperty(required = true) int capacity
) {}