package com.urlshortener.controller;

import com.urlshortener.controller.dto.ShortenRequest;
import com.urlshortener.controller.dto.ShortenResponse;
import com.urlshortener.controller.dto.StatsResponse;
import com.urlshortener.controller.dto.StatsResponse.ClickSummary;
import com.urlshortener.model.ShortenedUrl;
import com.urlshortener.service.UrlShortenerService;
import com.urlshortener.service.UrlShortenerService.Stats;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;
import java.util.Optional;

@RestController
public class UrlController {

    private final UrlShortenerService service;

    public UrlController(UrlShortenerService service) {
        this.service = service;
    }

    // ── M1: Shorten ────────────────────────────────────────────────────────

    @PostMapping("/api/shorten")
    public ResponseEntity<ShortenResponse> shorten(@Valid @RequestBody ShortenRequest req,
                                                    HttpServletRequest httpReq) {
        ShortenedUrl entity = service.shorten(
            req.getUrl(), req.getCustomAlias(), req.getTtlMinutes());

        String shortUrl = buildShortUrl(httpReq, entity.getShortCode());

        ShortenResponse resp = new ShortenResponse(
            entity.getShortCode(),
            shortUrl,
            entity.getOriginalUrl(),
            entity.getCreatedAt(),
            entity.getExpiresAt()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(resp);
    }

    // ── M2: Redirect ───────────────────────────────────────────────────────

    @GetMapping("/{shortCode}")
    public ResponseEntity<?> redirect(@PathVariable String shortCode,
                                      HttpServletRequest httpReq) {
        String referrer = httpReq.getHeader("Referer");
        String userAgent = httpReq.getHeader("User-Agent");

        Optional<ShortenedUrl> opt = service.resolveAndRecordClick(shortCode, referrer, userAgent);

        if (opt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(new Redirect404("Short code not found or expired", shortCode));
        }

        return ResponseEntity.status(HttpStatus.FOUND)  // 302
            .header(HttpHeaders.LOCATION, opt.get().getOriginalUrl())
            .build();
    }

    // ── M3: Stats ──────────────────────────────────────────────────────────

    @GetMapping("/api/stats/{shortCode}")
    public ResponseEntity<StatsResponse> stats(@PathVariable String shortCode) {
        Optional<Stats> opt = service.getStats(shortCode);
        if (opt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        Stats s = opt.get();
        List<ClickSummary> summaries = s.recentClicks().stream()
            .map(ce -> new ClickSummary(ce.getClickedAt(), ce.getReferrer(), ce.getUserAgent()))
            .toList();

        StatsResponse resp = new StatsResponse(
            s.shortCode(), s.originalUrl(), s.createdAt(), s.expiresAt(),
            s.expired(), s.totalClicks(), summaries
        );
        return ResponseEntity.ok(resp);
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    private String buildShortUrl(HttpServletRequest req, String shortCode) {
        String scheme = req.getScheme();        // http or https
        String host = req.getServerName();
        int port = req.getServerPort();
        boolean isStandard = (port == 80 && "http".equals(scheme))
                          || (port == 443 && "https".equals(scheme));
        return isStandard
            ? scheme + "://" + host + "/" + shortCode
            : scheme + "://" + host + ":" + port + "/" + shortCode;
    }

    /** Minimal JSON body for 404 redirect failures. */
    record Redirect404(String message, String shortCode) {}
}