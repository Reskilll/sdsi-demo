package com.mesterx.dashboard.repository;

import com.mesterx.dashboard.domain.ModelPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface ModelPriceRepository extends JpaRepository<ModelPrice, Long> {

    @Query("""
        select p from ModelPrice p
        where p.modelId = :modelId
          and p.validFrom <= :at
          and (p.validTo is null or p.validTo > :at)
        order by p.validFrom desc
        """)
    List<ModelPrice> findActiveAt(@Param("modelId") Long modelId, @Param("at") Instant at);

    @Query("""
        select p from ModelPrice p
        where p.modelId = :modelId
          and p.validTo is null
        order by p.validFrom desc
        """)
    List<ModelPrice> findCurrent(@Param("modelId") Long modelId);

    default Optional<ModelPrice> currentPrice(Long modelId, Instant at) {
        List<ModelPrice> prices = findActiveAt(modelId, at);
        return prices.stream().findFirst();
    }
}
