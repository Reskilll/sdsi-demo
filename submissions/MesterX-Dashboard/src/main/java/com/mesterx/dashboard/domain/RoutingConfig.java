package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "routing_configs")
public class RoutingConfig {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Enums.Scope scope;

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "worker_model_id", nullable = false)
    private Long workerModelId;

    @Column(name = "expert_model_id", nullable = false)
    private Long expertModelId;

    @Column(nullable = false)
    private int version = 1;

    @Column(name = "updated_by")
    private Long updatedBy;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    public Long getId() { return id; }
    public Enums.Scope getScope() { return scope; }
    public void setScope(Enums.Scope scope) { this.scope = scope; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getWorkerModelId() { return workerModelId; }
    public void setWorkerModelId(Long workerModelId) { this.workerModelId = workerModelId; }
    public Long getExpertModelId() { return expertModelId; }
    public void setExpertModelId(Long expertModelId) { this.expertModelId = expertModelId; }
    public int getVersion() { return version; }
    public void setVersion(int version) { this.version = version; }
    public Long getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(Long updatedBy) { this.updatedBy = updatedBy; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
