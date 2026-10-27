package com.urlshortener.repository;

import com.urlshortener.model.ClickEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface ClickEventRepository extends JpaRepository<ClickEvent, Long> {

    long countByShortCode(String shortCode);

    Optional<ClickEvent> findTopByShortCodeOrderByClickedAtDesc(String shortCode);

    @Query(value = "SELECT CAST(c.clicked_at AS DATE) AS click_day, COUNT(*) AS cnt " +
           "FROM click_events c WHERE c.short_code = :shortCode " +
           "GROUP BY CAST(c.clicked_at AS DATE) ORDER BY click_day ASC", nativeQuery = true)
    List<Object[]> countClicksPerDay(@Param("shortCode") String shortCode);

    // Count clicks since a given time (for expiry validation)
    long countByShortCodeAndClickedAtAfter(String shortCode, Instant after);

    // Get the most recent click for a code
    List<ClickEvent> findByShortCodeOrderByClickedAtDesc(String shortCode);
}