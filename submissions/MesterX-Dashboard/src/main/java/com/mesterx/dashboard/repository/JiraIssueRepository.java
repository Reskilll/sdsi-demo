package com.mesterx.dashboard.repository;

import com.mesterx.dashboard.domain.JiraIssue;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface JiraIssueRepository extends JpaRepository<JiraIssue, String> {

    @Query("""
        select i from JiraIssue i
        where i.assigneeUserId = :userId and i.projectId = :projectId
          and (i.resolvedAt is null or i.resolvedAt >= :from)
        order by i.updatedAt desc
        """)
    List<JiraIssue> findForDeveloper(@Param("userId") Long userId,
                                     @Param("projectId") Long projectId,
                                     @Param("from") java.time.Instant from);

    @Query("""
        select i from JiraIssue i
        where i.assigneeUserId = :userId
          and (i.resolvedAt is null or i.resolvedAt >= :from)
        order by i.updatedAt desc
        """)
    List<JiraIssue> findForDeveloperAllProjects(@Param("userId") Long userId,
                                                @Param("from") java.time.Instant from);

    @Query("""
        select count(i) from JiraIssue i
        where i.projectId = :projectId and i.assigneeUserId = :userId
        """)
    long countAssigned(@Param("projectId") Long projectId, @Param("userId") Long userId);

    @Query("""
        select count(i) from JiraIssue i
        where i.projectId = :projectId and i.assigneeUserId = :userId
          and i.statusCategory = com.mesterx.dashboard.domain.Enums.StatusCategory.DONE
          and i.resolvedAt >= :from and i.resolvedAt < :to
        """)
    long countDoneInRange(@Param("projectId") Long projectId, @Param("userId") Long userId,
                          @Param("from") java.time.Instant from, @Param("to") java.time.Instant to);
}
