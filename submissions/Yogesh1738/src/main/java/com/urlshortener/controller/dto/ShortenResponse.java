package com.urlshortener.controller.dto;

import java.time.Instant;

/**
 * Response returned after shortening a URL.
 */
public class ShortenResponse {

    private String shortCode;
    private String shortUrl;
    private String originalUrl;
    private Instant createdAt;
    private Instant expiresAt;

    public ShortenResponse(String shortCode, String shortUrl, String originalUrl,
                           Instant createdAt, Instant expiresAt) {
        this.shortCode = shortCode;
        this.shortUrl = shortUrl;
        this.originalUrl = originalUrl;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
    }

    public String getShortCode() { return shortCode; }
    public String getShortUrl() { return shortUrl; }
    public String getOriginalUrl() { return originalUrl; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
}