package com.urlshortener.util;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Set;

/**
 * M3 — Validates URLs: http/https only, rejects malformed / internal / opaque URIs.
 */
public final class UrlValidator {

    // These schemes are the only ones we accept
    private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");

    // Block common internal / private schemes that a naive URI parser would let through
    private static final Set<String> BLOCKED_SCHEMES = Set.of(
        "file", "ftp", "jar", "netdoc", "mailto", "javascript", "data"
    );

    // Maximum length for the whole URL to avoid DoS with giant strings
    private static final int MAX_URL_LENGTH = 2048;

    private UrlValidator() { /* utility class */ }

    /**
     * Run the full validation pipeline.
     * @param raw  the raw URL string from the request
     * @return the same string if valid
     * @throws IllegalArgumentException with a clear message on failure
     */
    public static String validate(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new IllegalArgumentException("URL must not be empty");
        }

        String trimmed = raw.trim();

        if (trimmed.length() > MAX_URL_LENGTH) {
            throw new IllegalArgumentException(
                "URL exceeds maximum length of " + MAX_URL_LENGTH + " characters");
        }

        // 1. Reject common dangerous schemes early — before parsing
        String lower = trimmed.toLowerCase();
        for (String blocked : BLOCKED_SCHEMES) {
            if (lower.startsWith(blocked + ":")) {
                throw new IllegalArgumentException(
                    "Scheme '" + blocked + "' is not allowed. Only http and https are supported.");
            }
        }

        // 2. Parse and enforce structure
        URI uri;
        try {
            uri = new URI(trimmed);
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("Malformed URL — " + e.getMessage());
        }

        // 3. Must have an absolute scheme
        String scheme = uri.getScheme();
        if (scheme == null) {
            throw new IllegalArgumentException("URL must include a scheme (http or https)");
        }

        // 4. Only http / https
        if (!ALLOWED_SCHEMES.contains(scheme.toLowerCase())) {
            throw new IllegalArgumentException(
                "Scheme '" + scheme + "' is not allowed. Only http and https are supported.");
        }

        // 5. Must have a host
        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new IllegalArgumentException("URL must include a host");
        }

        // 6. Reject loopback / link-local / site-local used as phishing bypass
        String hostLower = host.toLowerCase();
        if (hostLower.equals("localhost")
                || hostLower.equals("127.0.0.1")
                || hostLower.equals("0.0.0.0")
                || hostLower.equals("[::1]")
                || hostLower.startsWith("127.")
                || hostLower.startsWith("10.")
                || hostLower.startsWith("192.168.")
                || hostLower.startsWith("172.16.")
                || hostLower.startsWith("169.254.")) {
            throw new IllegalArgumentException("Internal / private hosts are not allowed");
        }

        // 7. Reject if the URI is opaque (no "/" authority) — e.g. "http:foo"
        if (uri.isOpaque()) {
            throw new IllegalArgumentException("Malformed URL — missing authority component");
        }

        return trimmed;
    }
}