package com.urlshortener.controller.dto;

import com.urlshortener.model.ClickEvent;

import java.time.Instant;
import java.util.List;

/**
 * Response returned for the stats endpoint.
 */
public class StatsResponse {

    private String shortCode;
    private String originalUrl;
    private Instant createdAt;
    private Instant expiresAt;
    private boolean expired;
    private long totalClicks;
    private List<ClickSummary> recentClicks;

    public StatsResponse(String shortCode, String originalUrl, Instant createdAt,
                          Instant expiresAt, boolean expired, long totalClicks,
                          List<ClickSummary> recentClicks) {
        this.shortCode = shortCode;
        this.originalUrl = originalUrl;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
        this.expired = expired;
        this.totalClicks = totalClicks;
        this.recentClicks = recentClicks;
    }

    public String getShortCode() { return shortCode; }
    public String getOriginalUrl() { return originalUrl; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public boolean isExpired() { return expired; }
    public long getTotalClicks() { return totalClicks; }
    public List<ClickSummary> getRecentClicks() { return recentClicks; }

    public record ClickSummary(Instant clickedAt, String referrer, String userAgent) {}
}