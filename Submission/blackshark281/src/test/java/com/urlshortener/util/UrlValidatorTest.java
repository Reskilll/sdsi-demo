package com.urlshortener.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

class UrlValidatorTest {

    @ParameterizedTest
    @ValueSource(strings = {
        "https://example.com",
        "http://example.com/path?q=1",
        "https://sub.example.co.uk/path/to/resource",
        "https://example.com:8080/path",
        "https://example.com/path#section",
        "example.com",                  // auto-prepends https://
        "example.com/path?q=1",
        "www.example.com"
    })
    void validUrls(String url) {
        String result = UrlValidator.validate(url);
        assertNotNull(result);
        assertTrue(result.startsWith("http://") || result.startsWith("https://"),
            "Validated URL should start with http:// or https://, got: " + result);
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "javascript:alert(1)",
        "javascript://comment%0Aalert(1)",
        "JaVaScRiPt:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "mailto:test@example.com",
        "tel:1234567890"
    })
    void blockedSchemes(String url) {
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate(url));
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"   ", "\t", "\n"})
    void blankUrls(String url) {
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate(url));
    }

    @Test
    void urlTooLong() {
        String longUrl = "https://example.com/" + "a".repeat(2100);
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate(longUrl));
    }
}