package com.urlshortener.service;

import com.urlshortener.model.ClickEvent;
import com.urlshortener.model.ShortenedUrl;
import com.urlshortener.repository.ClickEventRepository;
import com.urlshortener.repository.ShortenedUrlRepository;
import com.urlshortener.util.Base62;
import com.urlshortener.util.UrlValidator;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class UrlShortenerService {

    private final ShortenedUrlRepository urlRepo;
    private final ClickEventRepository clickRepo;

    public UrlShortenerService(ShortenedUrlRepository urlRepo, ClickEventRepository clickRepo) {
        this.urlRepo = urlRepo;
        this.clickRepo = clickRepo;
    }

    /* ---- M1: Shorten a URL ------------------------------------------------- */

    /**
     * Create a shortened URL.
     *
     * @param originalUrl  validated externally (controller)
     * @param customAlias  optional — if provided, used as-is instead of generating a code
     * @param ttlMinutes   optional expiry in minutes from now; null means no expiry
     * @return the persisted ShortenedUrl
     */
    public ShortenedUrl shorten(String originalUrl, String customAlias, Integer ttlMinutes) {
        // Validate the URL
        String validated = UrlValidator.validate(originalUrl);

        // Determine the short code
        String shortCode;
        if (customAlias != null && !customAlias.isBlank()) {
            String alias = customAlias.strip();
            if (alias.length() < 4 || alias.length() > 32) {
                throw new IllegalArgumentException("Custom alias must be 4–32 characters");
            }
            if (!alias.matches("[a-zA-Z0-9_-]+")) {
                throw new IllegalArgumentException(
                    "Custom alias can only contain letters, digits, underscores, and hyphens");
            }
            if (urlRepo.existsByShortCode(alias)) {
                throw new IllegalArgumentException("Custom alias '" + alias + "' is already taken");
            }
            shortCode = alias;
        } else {
            // Generate a Base62 code from a unique number: epoch milliseconds + hash
            shortCode = generateUniqueCode(validated);
        }

        Instant now = Instant.now();
        Instant expiresAt = ttlMinutes != null && ttlMinutes > 0
            ? now.plusSeconds(ttlMinutes * 60L)
            : null;

        ShortenedUrl entity = new ShortenedUrl(validated, shortCode, now, expiresAt);
        return urlRepo.save(entity);
    }

    /* ---- M2: Resolve / redirect -------------------------------------------- */

    /**
     * Look up the original URL for a short code, record a click, and return the entity.
     * Returns empty if the code doesn't exist or has expired.
     */
    public Optional<ShortenedUrl> resolveAndRecordClick(String shortCode,
                                                        String referrer,
                                                        String userAgent) {
        Optional<ShortenedUrl> opt = urlRepo.findByShortCode(shortCode);
        if (opt.isEmpty()) {
            return Optional.empty();
        }
        ShortenedUrl entity = opt.get();
        if (entity.isExpired()) {
            return Optional.empty();
        }

        // Record the click
        entity.setClickCount(entity.getClickCount() + 1);
        ClickEvent event = new ClickEvent(shortCode, Instant.now(),
            truncate(referrer, 64), truncate(userAgent, 256), entity);
        entity.getClickEvents().add(event);
        clickRepo.save(event);
        urlRepo.save(entity);

        return Optional.of(entity);
    }

    /* ---- M3: Stats --------------------------------------------------------- */

    /**
     * Return aggregate stats for a short code.
     */
    public Optional<Stats> getStats(String shortCode) {
        Optional<ShortenedUrl> opt = urlRepo.findByShortCode(shortCode);
        if (opt.isEmpty()) {
            return Optional.empty();
        }
        ShortenedUrl entity = opt.get();
        List<ClickEvent> recent = clickRepo
            .findByShortCodeOrderByClickedAtDesc(shortCode);

        return Optional.of(new Stats(
            entity.getShortCode(),
            entity.getOriginalUrl(),
            entity.getCreatedAt(),
            entity.getExpiresAt(),
            entity.isExpired(),
            entity.getClickCount(),
            recent
        ));
    }

    /* ---- Helpers ----------------------------------------------------------- */

    private String generateUniqueCode(String url) {
        // Build a unique seed: current time in millis + hash of URL
        long seed = Instant.now().toEpochMilli() + Math.abs((long) url.hashCode());
        String code = Base62.encode(seed);

        // Ensure 6-8 chars
        if (code.length() < 6) {
            code = padRight(code, 6);
        } else if (code.length() > 8) {
            code = code.substring(code.length() - 8);
        }

        // Extremely rare collision — retry with a tweaked seed
        int attempts = 0;
        while (urlRepo.existsByShortCode(code) && attempts < 5) {
            seed += 1 + (long) (Math.random() * 1000);
            code = Base62.encode(seed);
            if (code.length() > 8) code = code.substring(code.length() - 8);
            if (code.length() < 6) code = padRight(code, 6);
            attempts++;
        }
        if (urlRepo.existsByShortCode(code)) {
            throw new IllegalStateException(
                "Unable to generate a unique short code after " + attempts + " attempts");
        }
        return code;
    }

    private static String padRight(String s, int minLen) {
        StringBuilder sb = new StringBuilder(s);
        while (sb.length() < minLen) sb.append('0');
        return sb.toString();
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return null;
        return s.length() <= maxLen ? s : s.substring(0, maxLen);
    }

    /* ---- DTO --------------------------------------------------------------- */

    public record Stats(
        String shortCode,
        String originalUrl,
        Instant createdAt,
        Instant expiresAt,
        boolean expired,
        long totalClicks,
        List<ClickEvent> recentClicks
    ) {}
}