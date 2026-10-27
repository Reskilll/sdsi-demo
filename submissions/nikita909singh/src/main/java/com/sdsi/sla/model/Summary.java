package com.sdsi.sla.model;

import java.util.List;

/** Breach statistics (M5). Percentages are of all tickets in the bucket, open ones included. */
public record Summary(Bucket overall, List<Bucket> byPriority, List<Bucket> byAssigneeGroup) {

    public record Bucket(String key, int total, int breached, int open, double breachPercent) {
    }
}
