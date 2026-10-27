package com.sds.ebc.dto;

public record BidCheckRequest(
    String businessModel, String region, String source,
    String leaderId, double value, int startWeek, int durationWeeks, int priceMod
) {}
