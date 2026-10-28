package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.io.Serializable;
import java.util.Objects;

@Entity
@Table(name = "project_members")
@IdClass(ProjectMember.Pk.class)
public class ProjectMember {
    @Id
    @Column(name = "project_id")
    private Long projectId;

    @Id
    @Column(name = "user_id")
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(name = "role_in_project", nullable = false)
    private Enums.ProjectRole roleInProject;

    public ProjectMember() {}

    public ProjectMember(Long projectId, Long userId, Enums.ProjectRole roleInProject) {
        this.projectId = projectId;
        this.userId = userId;
        this.roleInProject = roleInProject;
    }

    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Enums.ProjectRole getRoleInProject() { return roleInProject; }
    public void setRoleInProject(Enums.ProjectRole roleInProject) { this.roleInProject = roleInProject; }

    public static class Pk implements Serializable {
        private Long projectId;
        private Long userId;

        public Pk() {}

        public Pk(Long projectId, Long userId) {
            this.projectId = projectId;
            this.userId = userId;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof Pk pk)) return false;
            return Objects.equals(projectId, pk.projectId) && Objects.equals(userId, pk.userId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(projectId, userId);
        }
    }
}
