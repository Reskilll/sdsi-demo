package com.mesterx.dashboard.repository;

import java.math.BigDecimal;

/** Projection used by UsageEventRepository.*ModelAgg* queries. */
public class ModelAgg {
    private final Long modelId;
    private final String tier;
    private final long tokens;
    private final BigDecimal cost;
    private final long requests;

    public ModelAgg(Long modelId, String tier, Long tokens, BigDecimal cost, Long requests) {
        this.modelId = modelId;
        this.tier = tier;
        this.tokens = tokens == null ? 0 : tokens;
        this.cost = cost == null ? BigDecimal.ZERO : cost;
        this.requests = requests == null ? 0 : requests;
    }

    public Long getModelId() { return modelId; }
    public String getTier() { return tier; }
    public long getTokens() { return tokens; }
    public BigDecimal getCost() { return cost; }
    public long getRequests() { return requests; }
}
