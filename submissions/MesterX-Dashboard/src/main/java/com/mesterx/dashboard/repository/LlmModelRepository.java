package com.mesterx.dashboard.repository;

import com.mesterx.dashboard.domain.Enums;
import com.mesterx.dashboard.domain.LlmModel;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface LlmModelRepository extends JpaRepository<LlmModel, Long> {
    Optional<LlmModel> findByName(String name);
    List<LlmModel> findByEnabledTrueOrderByName();
    List<LlmModel> findByTierAndEnabledTrueOrderByName(Enums.Tier tier);
}
