package com.urlshortener.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "click_events", indexes = { @Index(name = "idx_click_short_code", columnList = "shortCode") })
public class ClickEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 32)
    private String shortCode;

    @Column(nullable = false)
    private Instant clickedAt;

    @Column(length = 64)
    private String referrer;

    @Column(length = 256)
    private String userAgent;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "shortened_url_id")
    private ShortenedUrl shortenedUrl;

    public ClickEvent() {}

    public ClickEvent(String shortCode, Instant clickedAt, String referrer, String userAgent, ShortenedUrl shortenedUrl) {
        this.shortCode = shortCode;
        this.clickedAt = clickedAt;
        this.referrer = referrer;
        this.userAgent = userAgent;
        this.shortenedUrl = shortenedUrl;
    }

    // Getters / Setters ---------------------------------------------------

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getShortCode() { return shortCode; }
    public void setShortCode(String shortCode) { this.shortCode = shortCode; }

    public Instant getClickedAt() { return clickedAt; }
    public void setClickedAt(Instant clickedAt) { this.clickedAt = clickedAt; }

    public String getReferrer() { return referrer; }
    public void setReferrer(String referrer) { this.referrer = referrer; }

    public String getUserAgent() { return userAgent; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

    public ShortenedUrl getShortenedUrl() { return shortenedUrl; }
    public void setShortenedUrl(ShortenedUrl shortenedUrl) { this.shortenedUrl = shortenedUrl; }
}