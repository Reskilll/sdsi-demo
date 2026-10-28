package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

@Entity
@Table(name = "usage_events")
public class UsageEvent {
    @Id
    @Column(name = "event_id")
    private String eventId;

    @Column(nullable = false)
    private Instant ts;

    @Column(nullable = false)
    private LocalDate day;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "worker_model_id")
    private Long workerModelId;

    @Column(name = "expert_model_id")
    private Long expertModelId;

    @Column(name = "worker_in")
    private int workerIn;

    @Column(name = "worker_out")
    private int workerOut;

    @Column(name = "expert_in")
    private int expertIn;

    @Column(name = "expert_out")
    private int expertOut;

    @Column(name = "worker_latency_ms")
    private int workerLatencyMs;

    @Column(name = "expert_latency_ms")
    private int expertLatencyMs;

    @Column(name = "worker_cost_usd")
    private BigDecimal workerCostUsd = BigDecimal.ZERO;

    @Column(name = "expert_cost_usd")
    private BigDecimal expertCostUsd = BigDecimal.ZERO;

    @Column(name = "baseline_cost_usd")
    private BigDecimal baselineCostUsd = BigDecimal.ZERO;

    @Column(name = "savings_usd")
    private BigDecimal savingsUsd = BigDecimal.ZERO;

    @Column(name = "jira_key")
    private String jiraKey;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Enums.Outcome outcome;

    @Column(name = "plugin_version")
    private String pluginVersion;

    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }
    public Instant getTs() { return ts; }
    public void setTs(Instant ts) { this.ts = ts; }
    public LocalDate getDay() { return day; }
    public void setDay(LocalDate day) { this.day = day; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public Long getWorkerModelId() { return workerModelId; }
    public void setWorkerModelId(Long workerModelId) { this.workerModelId = workerModelId; }
    public Long getExpertModelId() { return expertModelId; }
    public void setExpertModelId(Long expertModelId) { this.expertModelId = expertModelId; }
    public int getWorkerIn() { return workerIn; }
    public void setWorkerIn(int workerIn) { this.workerIn = workerIn; }
    public int getWorkerOut() { return workerOut; }
    public void setWorkerOut(int workerOut) { this.workerOut = workerOut; }
    public int getExpertIn() { return expertIn; }
    public void setExpertIn(int expertIn) { this.expertIn = expertIn; }
    public int getExpertOut() { return expertOut; }
    public void setExpertOut(int expertOut) { this.expertOut = expertOut; }
    public int getWorkerLatencyMs() { return workerLatencyMs; }
    public void setWorkerLatencyMs(int workerLatencyMs) { this.workerLatencyMs = workerLatencyMs; }
    public int getExpertLatencyMs() { return expertLatencyMs; }
    public void setExpertLatencyMs(int expertLatencyMs) { this.expertLatencyMs = expertLatencyMs; }
    public BigDecimal getWorkerCostUsd() { return workerCostUsd; }
    public void setWorkerCostUsd(BigDecimal workerCostUsd) { this.workerCostUsd = workerCostUsd; }
    public BigDecimal getExpertCostUsd() { return expertCostUsd; }
    public void setExpertCostUsd(BigDecimal expertCostUsd) { this.expertCostUsd = expertCostUsd; }
    public BigDecimal getBaselineCostUsd() { return baselineCostUsd; }
    public void setBaselineCostUsd(BigDecimal baselineCostUsd) { this.baselineCostUsd = baselineCostUsd; }
    public BigDecimal getSavingsUsd() { return savingsUsd; }
    public void setSavingsUsd(BigDecimal savingsUsd) { this.savingsUsd = savingsUsd; }
    public String getJiraKey() { return jiraKey; }
    public void setJiraKey(String jiraKey) { this.jiraKey = jiraKey; }
    public Enums.Outcome getOutcome() { return outcome; }
    public void setOutcome(Enums.Outcome outcome) { this.outcome = outcome; }
    public String getPluginVersion() { return pluginVersion; }
    public void setPluginVersion(String pluginVersion) { this.pluginVersion = pluginVersion; }
}
