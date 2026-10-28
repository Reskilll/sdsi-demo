package com.mesterx.dashboard.repository;

import java.math.BigDecimal;

/** Projection used by UsageEventRepository.developersIn* queries. */
public class DeveloperAgg {
    private final Long userId;
    private final long workerTokens;
    private final long expertTokens;
    private final BigDecimal cost;
    private final BigDecimal savings;
    private final long requests;

    public DeveloperAgg(Long userId, Long workerTokens, Long expertTokens,
                        BigDecimal cost, BigDecimal savings, Long requests) {
        this.userId = userId;
        this.workerTokens = workerTokens == null ? 0 : workerTokens;
        this.expertTokens = expertTokens == null ? 0 : expertTokens;
        this.cost = cost == null ? BigDecimal.ZERO : cost;
        this.savings = savings == null ? BigDecimal.ZERO : savings;
        this.requests = requests == null ? 0 : requests;
    }

    public Long getUserId() { return userId; }
    public long getWorkerTokens() { return workerTokens; }
    public long getExpertTokens() { return expertTokens; }
    public BigDecimal getCost() { return cost; }
    public BigDecimal getSavings() { return savings; }
    public long getRequests() { return requests; }
}
