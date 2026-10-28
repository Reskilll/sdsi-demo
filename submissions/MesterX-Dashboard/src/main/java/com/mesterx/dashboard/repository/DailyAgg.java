package com.mesterx.dashboard.repository;

import java.math.BigDecimal;
import java.time.LocalDate;

/** Projection used by UsageEventRepository.daily* queries. */
public class DailyAgg {
    private final LocalDate day;
    private final long workerTokens;
    private final long expertTokens;
    private final BigDecimal cost;
    private final BigDecimal baselineCost;
    private final BigDecimal savings;
    private final long requests;

    public DailyAgg(LocalDate day, Long workerTokens, Long expertTokens,
                    BigDecimal cost, BigDecimal baselineCost, BigDecimal savings, Long requests) {
        this.day = day;
        this.workerTokens = workerTokens == null ? 0 : workerTokens;
        this.expertTokens = expertTokens == null ? 0 : expertTokens;
        this.cost = cost == null ? BigDecimal.ZERO : cost;
        this.baselineCost = baselineCost == null ? BigDecimal.ZERO : baselineCost;
        this.savings = savings == null ? BigDecimal.ZERO : savings;
        this.requests = requests == null ? 0 : requests;
    }

    public LocalDate getDay() { return day; }
    public long getWorkerTokens() { return workerTokens; }
    public long getExpertTokens() { return expertTokens; }
    public BigDecimal getCost() { return cost; }
    public BigDecimal getBaselineCost() { return baselineCost; }
    public BigDecimal getSavings() { return savings; }
    public long getRequests() { return requests; }
}
