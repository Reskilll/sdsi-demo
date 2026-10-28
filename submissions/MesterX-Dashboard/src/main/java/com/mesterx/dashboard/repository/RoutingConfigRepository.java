package com.mesterx.dashboard.repository;

import com.mesterx.dashboard.domain.Enums;
import com.mesterx.dashboard.domain.RoutingConfig;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface RoutingConfigRepository extends JpaRepository<RoutingConfig, Long> {
    Optional<RoutingConfig> findByScopeAndProjectIdIsNullAndUserIdIsNull(Enums.Scope scope);
    Optional<RoutingConfig> findByScopeAndProjectIdAndUserIdIsNull(Enums.Scope scope, Long projectId);
    Optional<RoutingConfig> findByScopeAndProjectIdAndUserId(Enums.Scope scope, Long projectId, Long userId);
}
