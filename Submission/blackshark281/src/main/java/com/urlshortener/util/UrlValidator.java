package com.urlshortener.util;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Set;

/**
 * Validates and normalizes URLs before shortening.
 * Only http and https schemes are accepted. Dangerous scheme-like patterns
 * (javascript:, data:, file:) are explicitly rejected.
 */
public final class UrlValidator {

    private static final Set<String> BLOCKED_SCHEMES = Set.of(
        "javascript", "data", "file", "ftp", "mailto", "tel", "about", "chrome", "edge"
    );

    private static final int MAX_URL_LENGTH = 2048;

    private UrlValidator() {
        // utility class
    }

    /**
     * Validate a URL string.
     *
     * @param url the URL to validate
     * @return the normalized URL string
     * @throws IllegalArgumentException if the URL is invalid or uses a blocked scheme
     */
    public static String validate(String url) throws IllegalArgumentException {
        if (url == null || url.isBlank()) {
            throw new IllegalArgumentException("URL must not be blank");
        }

        String trimmed = url.trim();

        // Block dangerous schemes even before parsing — catches javascript: and similar
        String lower = trimmed.toLowerCase();
        for (String blocked : BLOCKED_SCHEMES) {
            if (lower.startsWith(blocked + ":") || lower.startsWith(blocked + ":/")) {
                throw new IllegalArgumentException("URL scheme '" + blocked + "' is not allowed");
            }
        }

        if (trimmed.length() > MAX_URL_LENGTH) {
            throw new IllegalArgumentException(
                "URL length exceeds maximum of " + MAX_URL_LENGTH + " characters");
        }

        // Ensure URL has a scheme; default to https
        if (!trimmed.matches("(?i)^[a-z][a-z0-9+.-]*://.*")) {
            trimmed = "https://" + trimmed;
        }

        try {
            URI uri = new URI(trimmed);

            String scheme = uri.getScheme();
            if (scheme == null) {
                throw new IllegalArgumentException("URL must have a scheme");
            }
            scheme = scheme.toLowerCase();

            if (!scheme.equals("http") && !scheme.equals("https")) {
                throw new IllegalArgumentException("Only http and https schemes are allowed, got: " + scheme);
            }

            String host = uri.getHost();
            if (host == null || host.isEmpty()) {
                throw new IllegalArgumentException("URL must have a valid host");
            }

            // Reject URLs with bare IPs that are private/localhost (optional hardening)
            // Not strictly required but good practice

            // Convert to URL for additional validation
            uri.toURL();

            return trimmed;
        } catch (URISyntaxException | MalformedURLException e) {
            throw new IllegalArgumentException("Malformed URL: " + e.getMessage(), e);
        }
    }
}