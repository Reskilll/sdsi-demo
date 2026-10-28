package com.mesterx.dashboard.repository;

import com.mesterx.dashboard.domain.UsageEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface UsageEventRepository extends JpaRepository<UsageEvent, String> {

    Page<UsageEvent> findByProjectIdAndTsBetweenOrderByTsDesc(
            Long projectId, java.time.Instant from, java.time.Instant to, Pageable pageable);

    Page<UsageEvent> findByUserIdAndTsBetweenOrderByTsDesc(
            Long userId, java.time.Instant from, java.time.Instant to, Pageable pageable);

    Page<UsageEvent> findByTsBetweenOrderByTsDesc(
            java.time.Instant from, java.time.Instant to, Pageable pageable);

    // ---- aggregation (per scope) ----

    @Query("""
        select new com.mesterx.dashboard.repository.TokenAgg(
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd), 0), coalesce(sum(e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId = :projectId and e.day between :from and :to
        """)
    TokenAgg aggregateProject(@Param("projectId") Long projectId,
                              @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.TokenAgg(
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd), 0), coalesce(sum(e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId in :projectIds and e.day between :from and :to
        """)
    TokenAgg aggregateProjects(@Param("projectIds") List<Long> projectIds,
                               @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.TokenAgg(
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd), 0), coalesce(sum(e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.userId = :userId and e.day between :from and :to
        """)
    TokenAgg aggregateUser(@Param("userId") Long userId,
                           @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.TokenAgg(
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd), 0), coalesce(sum(e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId = :projectId and e.userId = :userId and e.day between :from and :to
        """)
    TokenAgg aggregateProjectUser(@Param("projectId") Long projectId, @Param("userId") Long userId,
                                  @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.TokenAgg(
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd), 0), coalesce(sum(e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.day between :from and :to
        """)
    TokenAgg aggregateAll(@Param("from") LocalDate from, @Param("to") LocalDate to);

    // ---- daily series ----

    @Query("""
        select new com.mesterx.dashboard.repository.DailyAgg(
            e.day,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId = :projectId and e.day between :from and :to
        group by e.day order by e.day
        """)
    List<DailyAgg> dailyProject(@Param("projectId") Long projectId,
                                @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.DailyAgg(
            e.day,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId in :projectIds and e.day between :from and :to
        group by e.day order by e.day
        """)
    List<DailyAgg> dailyProjects(@Param("projectIds") List<Long> projectIds,
                                 @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.DailyAgg(
            e.day,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.userId = :userId and e.day between :from and :to
        group by e.day order by e.day
        """)
    List<DailyAgg> dailyUser(@Param("userId") Long userId,
                             @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.DailyAgg(
            e.day,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0),
            coalesce(sum(e.baselineCostUsd), 0), coalesce(sum(e.savingsUsd), 0), count(e))
        from UsageEvent e
        where e.projectId = :projectId and e.userId = :userId and e.day between :from and :to
        group by e.day order by e.day
        """)
    List<DailyAgg> dailyProjectUser(@Param("projectId") Long projectId, @Param("userId") Long userId,
                                    @Param("from") LocalDate from, @Param("to") LocalDate to);

    // ---- per-developer ----

    @Query("""
        select new com.mesterx.dashboard.repository.DeveloperAgg(
            e.userId,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0), coalesce(sum(e.savingsUsd), 0),
            count(e))
        from UsageEvent e
        where e.projectId = :projectId and e.day between :from and :to
        group by e.userId
        """)
    List<DeveloperAgg> developersInProject(@Param("projectId") Long projectId,
                                           @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.DeveloperAgg(
            e.userId,
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.expertIn + e.expertOut), 0),
            coalesce(sum(e.workerCostUsd + e.expertCostUsd), 0), coalesce(sum(e.savingsUsd), 0),
            count(e))
        from UsageEvent e
        where e.projectId in :projectIds and e.day between :from and :to
        group by e.userId
        """)
    List<DeveloperAgg> developersInProjects(@Param("projectIds") List<Long> projectIds,
                                            @Param("from") LocalDate from, @Param("to") LocalDate to);

    // ---- per-model ----

    @Query("""
        select new com.mesterx.dashboard.repository.ModelAgg(
            e.workerModelId, 'WORKER',
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.workerCostUsd), 0), count(e))
        from UsageEvent e
        where e.projectId in :projectIds and e.day between :from and :to
        group by e.workerModelId
        """)
    List<ModelAgg> workerModelAggProjects(@Param("projectIds") List<Long> projectIds,
                                          @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.ModelAgg(
            e.expertModelId, 'EXPERT',
            coalesce(sum(e.expertIn + e.expertOut), 0), coalesce(sum(e.expertCostUsd), 0), count(e))
        from UsageEvent e
        where e.projectId in :projectIds and e.day between :from and :to
        group by e.expertModelId
        """)
    List<ModelAgg> expertModelAggProjects(@Param("projectIds") List<Long> projectIds,
                                          @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.ModelAgg(
            e.workerModelId, 'WORKER',
            coalesce(sum(e.workerIn + e.workerOut), 0), coalesce(sum(e.workerCostUsd), 0), count(e))
        from UsageEvent e
        where e.userId = :userId and e.day between :from and :to
        group by e.workerModelId
        """)
    List<ModelAgg> workerModelAggUser(@Param("userId") Long userId,
                                      @Param("from") LocalDate from, @Param("to") LocalDate to);

    @Query("""
        select new com.mesterx.dashboard.repository.ModelAgg(
            e.expertModelId, 'EXPERT',
            coalesce(sum(e.expertIn + e.expertOut), 0), coalesce(sum(e.expertCostUsd), 0), count(e))
        from UsageEvent e
        where e.userId = :userId and e.day between :from and :to
        group by e.expertModelId
        """)
    List<ModelAgg> expertModelAggUser(@Param("userId") Long userId,
                                      @Param("from") LocalDate from, @Param("to") LocalDate to);

    long countByProjectIdAndDayBetween(Long projectId, LocalDate from, LocalDate to);
    long countByUserIdAndDayBetween(Long userId, LocalDate from, LocalDate to);
}
