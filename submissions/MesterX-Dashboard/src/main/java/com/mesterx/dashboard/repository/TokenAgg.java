package com.mesterx.dashboard.repository;

import java.math.BigDecimal;

/** Projection used by UsageEventRepository.aggregate* queries. */
public class TokenAgg {
    private final long workerTokens;
    private final long expertTokens;
    private final BigDecimal workerCost;
    private final BigDecimal expertCost;
    private final BigDecimal baselineCost;
    private final BigDecimal savings;
    private final long requests;

    public TokenAgg(Long workerTokens, Long expertTokens,
                    BigDecimal workerCost, BigDecimal expertCost,
                    BigDecimal baselineCost, BigDecimal savings, Long requests) {
        this.workerTokens = workerTokens == null ? 0 : workerTokens;
        this.expertTokens = expertTokens == null ? 0 : expertTokens;
        this.workerCost = workerCost == null ? BigDecimal.ZERO : workerCost;
        this.expertCost = expertCost == null ? BigDecimal.ZERO : expertCost;
        this.baselineCost = baselineCost == null ? BigDecimal.ZERO : baselineCost;
        this.savings = savings == null ? BigDecimal.ZERO : savings;
        this.requests = requests == null ? 0 : requests;
    }

    public long getWorkerTokens() { return workerTokens; }
    public long getExpertTokens() { return expertTokens; }
    public long getTotalTokens() { return workerTokens + expertTokens; }
    public BigDecimal getWorkerCost() { return workerCost; }
    public BigDecimal getExpertCost() { return expertCost; }
    public BigDecimal getTotalCost() { return workerCost.add(expertCost); }
    public BigDecimal getBaselineCost() { return baselineCost; }
    public BigDecimal getSavings() { return savings; }
    public long getRequests() { return requests; }
}
