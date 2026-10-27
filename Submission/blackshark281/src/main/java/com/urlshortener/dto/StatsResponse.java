package com.urlshortener.dto;

import java.util.Map;

public class StatsResponse {

    private String shortCode;
    private String originalUrl;
    private long totalClicks;
    private String lastAccessedAt;
    private Map<String, Long> clicksPerDay;
    private String createdAt;
    private String expiresAt;
    private boolean expired;

    public StatsResponse() {
    }

    public StatsResponse(String shortCode, String originalUrl, long totalClicks,
                         String lastAccessedAt, Map<String, Long> clicksPerDay,
                         String createdAt, String expiresAt, boolean expired) {
        this.shortCode = shortCode;
        this.originalUrl = originalUrl;
        this.totalClicks = totalClicks;
        this.lastAccessedAt = lastAccessedAt;
        this.clicksPerDay = clicksPerDay;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
        this.expired = expired;
    }

    public String getShortCode() {
        return shortCode;
    }

    public void setShortCode(String shortCode) {
        this.shortCode = shortCode;
    }

    public String getOriginalUrl() {
        return originalUrl;
    }

    public void setOriginalUrl(String originalUrl) {
        this.originalUrl = originalUrl;
    }

    public long getTotalClicks() {
        return totalClicks;
    }

    public void setTotalClicks(long totalClicks) {
        this.totalClicks = totalClicks;
    }

    public String getLastAccessedAt() {
        return lastAccessedAt;
    }

    public void setLastAccessedAt(String lastAccessedAt) {
        this.lastAccessedAt = lastAccessedAt;
    }

    public Map<String, Long> getClicksPerDay() {
        return clicksPerDay;
    }

    public void setClicksPerDay(Map<String, Long> clicksPerDay) {
        this.clicksPerDay = clicksPerDay;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(String expiresAt) {
        this.expiresAt = expiresAt;
    }

    public boolean isExpired() {
        return expired;
    }

    public void setExpired(boolean expired) {
        this.expired = expired;
    }
}