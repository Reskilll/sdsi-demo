package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "jira_issues")
public class JiraIssue {
    @Id
    @Column(name = "issue_key")
    private String key;

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "assignee_user_id")
    private Long assigneeUserId;

    @Column(name = "assignee_account")
    private String assigneeAccount;

    private String summary;
    private String status;

    @Enumerated(EnumType.STRING)
    @Column(name = "status_category")
    private Enums.StatusCategory statusCategory;

    @Column(name = "issue_type")
    private String issueType;

    @Column(name = "created_at")
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    @Column(name = "resolved_at")
    private Instant resolvedAt;

    @Column(name = "synced_at")
    private Instant syncedAt;

    private String url;

    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public Long getAssigneeUserId() { return assigneeUserId; }
    public void setAssigneeUserId(Long assigneeUserId) { this.assigneeUserId = assigneeUserId; }
    public String getAssigneeAccount() { return assigneeAccount; }
    public void setAssigneeAccount(String assigneeAccount) { this.assigneeAccount = assigneeAccount; }
    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Enums.StatusCategory getStatusCategory() { return statusCategory; }
    public void setStatusCategory(Enums.StatusCategory statusCategory) { this.statusCategory = statusCategory; }
    public String getIssueType() { return issueType; }
    public void setIssueType(String issueType) { this.issueType = issueType; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant resolvedAt) { this.resolvedAt = resolvedAt; }
    public Instant getSyncedAt() { return syncedAt; }
    public void setSyncedAt(Instant syncedAt) { this.syncedAt = syncedAt; }
    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
}
