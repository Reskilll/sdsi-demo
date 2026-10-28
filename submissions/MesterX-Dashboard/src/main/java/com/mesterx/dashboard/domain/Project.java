package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "projects")
public class Project {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_key", nullable = false, unique = true)
    private String key;

    @Column(nullable = false)
    private String name;

    @Column(name = "jira_project_key")
    private String jiraProjectKey;

    @Column(name = "budget_usd")
    private BigDecimal budgetUsd;

    @Column(name = "alert_pct", nullable = false)
    private int alertPct = 80;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    public Long getId() { return id; }
    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getJiraProjectKey() { return jiraProjectKey; }
    public void setJiraProjectKey(String jiraProjectKey) { this.jiraProjectKey = jiraProjectKey; }
    public BigDecimal getBudgetUsd() { return budgetUsd; }
    public void setBudgetUsd(BigDecimal budgetUsd) { this.budgetUsd = budgetUsd; }
    public int getAlertPct() { return alertPct; }
    public void setAlertPct(int alertPct) { this.alertPct = alertPct; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
