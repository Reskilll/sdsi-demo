package com.sds.ebc.dto;

public record DashboardStats(
    long totalOpportunities, long openCount, long wonCount, long lostCount, long droppedCount,
    double totalWonValue, double totalOpenValue, double winRate,
    double weightedPipeline, int avgCycleDays
) {}
