package com.urlshortener.service;

import com.urlshortener.dto.ShortenRequest;
import com.urlshortener.dto.ShortenResponse;
import com.urlshortener.dto.StatsResponse;
import com.urlshortener.model.ClickEvent;
import com.urlshortener.model.ShortenedUrl;
import com.urlshortener.repository.ClickEventRepository;
import com.urlshortener.repository.ShortenedUrlRepository;
import com.urlshortener.util.Base62Encoder;
import com.urlshortener.util.UrlValidator;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
public class UrlShortenerService {

    private final ShortenedUrlRepository urlRepository;
    private final ClickEventRepository clickRepository;
    private final DateTimeFormatter dateFmt = DateTimeFormatter.ISO_LOCAL_DATE;

    // Must not collide with a base62-encoded DB id. A 4-char alias is safe
    // because the auto-generated codes are >= 6 chars via Base62Encoder.MIN_LENGTH.
    private static final String STATS_PREFIX = "stats";

    public UrlShortenerService(ShortenedUrlRepository urlRepository,
                               ClickEventRepository clickRepository) {
        this.urlRepository = urlRepository;
        this.clickRepository = clickRepository;
    }

    /**
     * Shorten a URL. Idempotent for the same URL without a custom alias.
     */
    @Transactional
    public ShortenResponse shorten(ShortenRequest request, String baseUrl) {
        String originalUrl = UrlValidator.validate(request.getUrl());

        Integer expiryDays = request.getExpiryDays();
        if (expiryDays != null && expiryDays < 1) {
            throw new IllegalArgumentException("Expiry days must be at least 1");
        }

        Instant expiresAt = null;
        if (expiryDays != null) {
            expiresAt = Instant.now().plusSeconds(expiryDays * 86400L);
        }

        // --- Custom alias path ---
        if (request.getCustomAlias() != null && !request.getCustomAlias().isBlank()) {
            return shortenWithAlias(originalUrl, request.getCustomAlias().trim(), expiresAt, baseUrl);
        }

        // --- Auto-generate path: idempotent lookup ---
        Optional<ShortenedUrl> existing = urlRepository
            .findByOriginalUrlAndIsCustomAliasFalse(originalUrl);

        if (existing.isPresent()) {
            ShortenedUrl su = existing.get();
            // If the old one expired, treat it as a fresh shorten but reuse the code
            if (su.isExpired()) {
                su.setCreatedAt(Instant.now());
                su.setExpiresAt(expiresAt);
                su.setClickCount(0);
                urlRepository.save(su);
            }
            return toResponse(su, baseUrl);
        }

        // New auto code: save with placeholder, get DB id, then set real code
        String placeholder = "TMP" + System.nanoTime() % 10_000_000;
        ShortenedUrl entity = new ShortenedUrl(originalUrl, placeholder, expiresAt, false);
        entity = urlRepository.save(entity);          // get DB id
        String code = Base62Encoder.encode(entity.getId());
        entity.setShortCode(code);
        entity = urlRepository.save(entity);

        return toResponse(entity, baseUrl);
    }

    private ShortenResponse shortenWithAlias(String originalUrl, String alias, Instant expiresAt, String baseUrl) {
        if (alias.length() < 4) {
            throw new IllegalArgumentException("Custom alias must be at least 4 characters");
        }
        if (!alias.matches("^[a-zA-Z0-9_-]+$")) {
            throw new IllegalArgumentException(
                "Custom alias must contain only alphanumeric characters, hyphens, and underscores");
        }

        // Block aliases that could collide with reserved functionality
        if (isReserved(alias)) {
            throw new IllegalArgumentException("The alias '" + alias + "' is reserved");
        }

        Optional<ShortenedUrl> existingByAlias = urlRepository.findByShortCode(alias);
        if (existingByAlias.isPresent()) {
            ShortenedUrl su = existingByAlias.get();
            // If it's the same URL, return it (idempotent for custom alias)
            if (su.getOriginalUrl().equals(originalUrl)) {
                return toResponse(su, baseUrl);
            }
            throw new IllegalArgumentException(
                "Custom alias '" + alias + "' is already in use");
        }

        ShortenedUrl entity = new ShortenedUrl(originalUrl, alias, expiresAt, true);
        urlRepository.save(entity);
        return toResponse(entity, baseUrl);
    }

    /**
     * Resolve a short code: return the original URL or throw an exception
     * indicating the appropriate HTTP status.
     */
    @Transactional
    public String resolve(String code, HttpServletRequest request) {
        if (code == null || code.isBlank()) {
            throw new NotFoundException("No short code provided");
        }

        if (code.startsWith(STATS_PREFIX)) {
            throw new NotFoundException("Not a valid short code");
        }

        ShortenedUrl su = urlRepository.findByShortCode(code)
            .orElseThrow(() -> new NotFoundException("Short code not found: " + code));

        if (su.isExpired()) {
            throw new GoneException("This link has expired");   // 410
        }

        // Record click event
        String referer = truncate(request.getHeader("Referer"), 256);
        String userAgent = truncate(request.getHeader("User-Agent"), 128);

        ClickEvent event = new ClickEvent(code, referer, userAgent);
        clickRepository.save(event);

        // Update aggregate counters
        su.setClickCount(su.getClickCount() + 1);
        su.setLastAccessedAt(Instant.now());
        urlRepository.save(su);

        return su.getOriginalUrl();
    }

    /**
     * Get stats for a short code.
     */
    @Transactional(readOnly = true)
    public StatsResponse getStats(String code) {
        ShortenedUrl su = urlRepository.findByShortCode(code)
            .orElseThrow(() -> new NotFoundException("Short code not found: " + code));

        String lastAccessed = su.getLastAccessedAt() != null
            ? su.getLastAccessedAt().toString()
            : null;

        Map<String, Long> clicksPerDay = new LinkedHashMap<>();

        List<Object[]> rows = clickRepository.countClicksPerDay(code);
        for (Object[] row : rows) {
            String day = row[0].toString();  // e.g. "2026-10-27"
            long count = ((Number) row[1]).longValue();
            clicksPerDay.put(day, count);
        }

        return new StatsResponse(
            su.getShortCode(),
            su.getOriginalUrl(),
            su.getClickCount(),
            lastAccessed,
            clicksPerDay,
            su.getCreatedAt().toString(),
            su.getExpiresAt() != null ? su.getExpiresAt().toString() : null,
            su.isExpired()
        );
    }

    // ===== helpers =====

    private ShortenResponse toResponse(ShortenedUrl su, String baseUrl) {
        String shortUrl = baseUrl + "/" + su.getShortCode();
        return new ShortenResponse(
            su.getShortCode(),
            shortUrl,
            su.getOriginalUrl(),
            su.getCreatedAt().toString(),
            su.getExpiresAt() != null ? su.getExpiresAt().toString() : null
        );
    }

    private boolean isReserved(String alias) {
        String lower = alias.toLowerCase();
        return lower.startsWith("stats") || lower.startsWith("api") || lower.startsWith("admin");
    }

    private String truncate(String value, int maxLen) {
        if (value == null) return null;
        return value.length() > maxLen ? value.substring(0, maxLen) : value;
    }

    // ===== exception types =====

    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) {
            super(message);
        }
    }

    public static class GoneException extends RuntimeException {
        public GoneException(String message) {
            super(message);
        }
    }
}