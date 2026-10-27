package com.urlshortener.service;

import com.urlshortener.dto.ShortenRequest;
import com.urlshortener.dto.ShortenResponse;
import com.urlshortener.dto.StatsResponse;
import com.urlshortener.model.ClickEvent;
import com.urlshortener.model.ShortenedUrl;
import com.urlshortener.repository.ClickEventRepository;
import com.urlshortener.repository.ShortenedUrlRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UrlShortenerServiceTest {

    @Mock
    private ShortenedUrlRepository urlRepository;

    @Mock
    private ClickEventRepository clickRepository;

    @InjectMocks
    private UrlShortenerService service;

    private static final String BASE_URL = "http://localhost:8080";

    @BeforeEach
    void setUp() {
        // URL validator will auto-prepend https:// to bare domains
    }

    // ===== Shorten tests =====

    @Test
    void shortenValidUrl() {
        when(urlRepository.findByOriginalUrlAndIsCustomAliasFalse("https://example.com"))
            .thenReturn(Optional.empty());

        ShortenedUrl saved = new ShortenedUrl("https://example.com", "000001", null, false);
        saved.setId(1L);
        when(urlRepository.save(any(ShortenedUrl.class))).thenReturn(saved);

        ShortenRequest req = new ShortenRequest("https://example.com", null, null);
        ShortenResponse resp = service.shorten(req, BASE_URL);

        assertNotNull(resp.getShortCode());
        assertEquals("https://example.com", resp.getOriginalUrl());
        assertTrue(resp.getShortUrl().contains(BASE_URL));
    }

    @Test
    void shortenSameUrlTwiceIsIdempotent() {
        // First call
        when(urlRepository.findByOriginalUrlAndIsCustomAliasFalse("https://example.com"))
            .thenReturn(Optional.empty());

        ShortenedUrl saved = new ShortenedUrl("https://example.com", "000001", null, false);
        saved.setId(1L);
        when(urlRepository.save(any(ShortenedUrl.class))).thenReturn(saved);

        ShortenRequest req = new ShortenRequest("https://example.com", null, null);
        ShortenResponse first = service.shorten(req, BASE_URL);

        verify(urlRepository).findByOriginalUrlAndIsCustomAliasFalse("https://example.com");

        // Second call — same URL should return the same code
        reset(urlRepository);
        ShortenedUrl existing = new ShortenedUrl("https://example.com", "000001", null, false);
        existing.setId(1L);
        when(urlRepository.findByOriginalUrlAndIsCustomAliasFalse("https://example.com"))
            .thenReturn(Optional.of(existing));

        ShortenResponse second = service.shorten(req, BASE_URL);

        assertEquals(first.getShortCode(), second.getShortCode(),
            "Same URL without custom alias should produce the same short code");
    }

    @Test
    void shortenWithCustomAlias() {
        ShortenRequest req = new ShortenRequest("https://example.com", "myLink", null);
        when(urlRepository.findByShortCode("myLink")).thenReturn(Optional.empty());
        when(urlRepository.save(any(ShortenedUrl.class))).thenAnswer(inv -> inv.getArgument(0));

        ShortenResponse resp = service.shorten(req, BASE_URL);
        assertEquals("myLink", resp.getShortCode());
    }

    @Test
    void shortenWithDuplicateCustomAliasThrows() {
        ShortenRequest req = new ShortenRequest("https://example.com", "myLink", null);
        ShortenedUrl existing = new ShortenedUrl("https://other.com", "myLink", null, true);
        when(urlRepository.findByShortCode("myLink")).thenReturn(Optional.of(existing));

        assertThrows(IllegalArgumentException.class, () -> service.shorten(req, BASE_URL));
    }

    @Test
    void shortenWithExpiry() {
        when(urlRepository.findByOriginalUrlAndIsCustomAliasFalse("https://example.com"))
            .thenReturn(Optional.empty());

        ShortenedUrl saved = new ShortenedUrl("https://example.com", "000001",
            Instant.now().plus(7, ChronoUnit.DAYS), false);
        saved.setId(1L);
        when(urlRepository.save(any(ShortenedUrl.class))).thenReturn(saved);

        ShortenRequest req = new ShortenRequest("https://example.com", null, 7);
        ShortenResponse resp = service.shorten(req, BASE_URL);

        assertNotNull(resp.getExpiresAt());
    }

    @Test
    void shortenBlockedScheme() {
        ShortenRequest req = new ShortenRequest("javascript:alert(1)", null, null);
        assertThrows(IllegalArgumentException.class, () -> service.shorten(req, BASE_URL));
    }

    @Test
    void shortenInvalidExpiry() {
        ShortenRequest req = new ShortenRequest("https://example.com", null, -1);
        assertThrows(IllegalArgumentException.class, () -> service.shorten(req, BASE_URL));
    }

    @Test
    void shortenReservedAlias() {
        ShortenRequest req = new ShortenRequest("https://example.com", "statsX", null);
        assertThrows(IllegalArgumentException.class, () -> service.shorten(req, BASE_URL));
    }

    // ===== Resolve tests =====

    @Test
    void resolveValidCode() {
        ShortenedUrl su = new ShortenedUrl("https://example.com", "abc123", null, false);
        when(urlRepository.findByShortCode("abc123")).thenReturn(Optional.of(su));

        MockHttpServletRequest request = new MockHttpServletRequest();

        String resolved = service.resolve("abc123", request);
        assertEquals("https://example.com", resolved);

        verify(clickRepository).save(any(ClickEvent.class));
    }

    @Test
    void resolveUnknownCode() {
        when(urlRepository.findByShortCode("unknown")).thenReturn(Optional.empty());

        assertThrows(UrlShortenerService.NotFoundException.class,
            () -> service.resolve("unknown", new MockHttpServletRequest()));
    }

    @Test
    void resolveExpiredCode() {
        ShortenedUrl su = new ShortenedUrl("https://example.com", "abc123",
            Instant.now().minus(1, ChronoUnit.DAYS), false);
        when(urlRepository.findByShortCode("abc123")).thenReturn(Optional.of(su));

        assertThrows(UrlShortenerService.GoneException.class,
            () -> service.resolve("abc123", new MockHttpServletRequest()));
    }

    @Test
    void resolveRecordsClick() {
        ShortenedUrl su = new ShortenedUrl("https://example.com", "abc123", null, false);
        when(urlRepository.findByShortCode("abc123")).thenReturn(Optional.of(su));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Referer", "https://google.com");
        request.addHeader("User-Agent", "Mozilla/5.0");

        service.resolve("abc123", request);

        ArgumentCaptor<ClickEvent> captor = ArgumentCaptor.forClass(ClickEvent.class);
        verify(clickRepository).save(captor.capture());
        ClickEvent event = captor.getValue();

        assertEquals("abc123", event.getShortCode());
        assertEquals("https://google.com", event.getReferer());
    }

    // ===== Stats tests =====

    @Test
    void getStats() {
        ShortenedUrl su = new ShortenedUrl("https://example.com", "abc123", null, false);
        su.setClickCount(5);
        su.setLastAccessedAt(Instant.now());
        when(urlRepository.findByShortCode("abc123")).thenReturn(Optional.of(su));
        when(clickRepository.countClicksPerDay("abc123")).thenReturn(java.util.List.of());

        StatsResponse stats = service.getStats("abc123");
        assertEquals("abc123", stats.getShortCode());
        assertEquals(5, stats.getTotalClicks());
    }
}