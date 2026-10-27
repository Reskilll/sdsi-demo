package com.urlshortener.controller;

import com.urlshortener.dto.ShortenRequest;
import com.urlshortener.dto.ShortenResponse;
import com.urlshortener.dto.StatsResponse;
import com.urlshortener.service.UrlShortenerService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.HashMap;
import java.util.Map;

@RestController
public class UrlShortenerController {

    private final UrlShortenerService service;

    public UrlShortenerController(UrlShortenerService service) {
        this.service = service;
    }

    /**
     * POST /api/shorten — shorten a URL.
     */
    @PostMapping("/api/shorten")
    public ResponseEntity<ShortenResponse> shorten(@Valid @RequestBody ShortenRequest request,
                                                   HttpServletRequest req) {
        String baseUrl = getBaseUrl(req);
        ShortenResponse response = service.shorten(request, baseUrl);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * GET /api/stats/{code} — get click statistics for a short code.
     */
    @GetMapping("/api/stats/{code}")
    public ResponseEntity<StatsResponse> stats(@PathVariable String code) {
        StatsResponse response = service.getStats(code);
        return ResponseEntity.ok(response);
    }

    /**
     * GET /{code} — resolve a short code and redirect.
     */
    @GetMapping("/{code}")
    public ResponseEntity<Void> resolve(@PathVariable String code, HttpServletRequest request) {
        String originalUrl = service.resolve(code, request);
        return ResponseEntity.status(HttpStatus.FOUND)
            .location(URI.create(originalUrl))
            .build();
    }

    // ===== Exception handlers =====

    @ExceptionHandler(UrlShortenerService.NotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(UrlShortenerService.NotFoundException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("status", 404);
        body.put("error", "Not Found");
        body.put("message", ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(body);
    }

    @ExceptionHandler(UrlShortenerService.GoneException.class)
    public ResponseEntity<Map<String, Object>> handleGone(UrlShortenerService.GoneException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("status", 410);
        body.put("error", "Gone");
        body.put("message", ex.getMessage());
        return ResponseEntity.status(HttpStatus.GONE).body(body);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("status", 400);
        body.put("error", "Bad Request");
        body.put("message", ex.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(body);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, Object> body = new HashMap<>();
        body.put("status", 400);
        body.put("error", "Validation Error");
        Map<String, String> fieldErrors = new HashMap<>();
        for (FieldError fe : ex.getBindingResult().getFieldErrors()) {
            fieldErrors.put(fe.getField(), fe.getDefaultMessage());
        }
        body.put("fields", fieldErrors);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(body);
    }

    // ===== helpers =====

    private String getBaseUrl(HttpServletRequest req) {
        String scheme = req.getScheme();
        String host = req.getHeader("X-Forwarded-Host");
        if (host == null || host.isBlank()) {
            host = req.getServerName();
            if (req.getServerPort() != 80 && req.getServerPort() != 443) {
                host += ":" + req.getServerPort();
            }
        }
        return scheme + "://" + host;
    }
}