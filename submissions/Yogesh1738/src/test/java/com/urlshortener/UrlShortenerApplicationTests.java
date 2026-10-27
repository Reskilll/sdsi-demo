package com.urlshortener;

import com.urlshortener.util.Base62;
import com.urlshortener.util.UrlValidator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

class UrlShortenerApplicationTests {

    // ── Base62 ──────────────────────────────────────────────────

    @Test
    void base62EncodeDecode() {
        long id = 916132832L;
        String code = Base62.encode(id);
        assertNotNull(code);
        assertTrue(code.length() >= 6 && code.length() <= 8,
            "Expected 6-8 chars, got " + code.length() + ": " + code);
        assertEquals(id, Base62.decode(code));
    }

    @Test
    void base62Zero() {
        assertEquals("0", Base62.encode(0));
        assertEquals(0, Base62.decode("0"));
    }

    @Test
    void base62NegativeThrows() {
        assertThrows(IllegalArgumentException.class, () -> Base62.encode(-1));
    }

    // ── URL Validation ──────────────────────────────────────────

    @ParameterizedTest
    @ValueSource(strings = {
        "https://example.com",
        "http://example.com/path?q=1",
        "https://sub.domain.example.com:8443/page",
        "HTTPS://EXAMPLE.COM",         // case-insensitive scheme
    })
    void validUrls(String url) {
        assertEquals(url, UrlValidator.validate(url));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "ftp://files.example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "//evil.com",                  // no scheme
        "not-a-url",
        "",
    })
    void invalidUrls(String url) {
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate(url));
    }

    @Test
    void rejectsEmptyAndNull() {
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate(null));
        assertThrows(IllegalArgumentException.class, () -> UrlValidator.validate("   "));
    }

    @Test
    void rejectsPrivateHosts() {
        assertThrows(IllegalArgumentException.class,
            () -> UrlValidator.validate("http://localhost/admin"));
        assertThrows(IllegalArgumentException.class,
            () -> UrlValidator.validate("http://127.0.0.1/admin"));
        assertThrows(IllegalArgumentException.class,
            () -> UrlValidator.validate("http://192.168.1.1/admin"));
    }
}