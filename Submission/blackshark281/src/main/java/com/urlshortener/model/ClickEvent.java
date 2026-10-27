package com.urlshortener.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "click_events", indexes = {
    @Index(name = "idx_click_short_code", columnList = "shortCode"),
    @Index(name = "idx_click_timestamp", columnList = "clickedAt")
})
public class ClickEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 30)
    private String shortCode;

    @Column(nullable = false)
    private Instant clickedAt;

    @Column(length = 256)
    private String referer;

    @Column(length = 128)
    private String userAgent;

    public ClickEvent() {
    }

    public ClickEvent(String shortCode, String referer, String userAgent) {
        this.shortCode = shortCode;
        this.clickedAt = Instant.now();
        this.referer = referer;
        this.userAgent = userAgent;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getShortCode() {
        return shortCode;
    }

    public void setShortCode(String shortCode) {
        this.shortCode = shortCode;
    }

    public Instant getClickedAt() {
        return clickedAt;
    }

    public void setClickedAt(Instant clickedAt) {
        this.clickedAt = clickedAt;
    }

    public String getReferer() {
        return referer;
    }

    public void setReferer(String referer) {
        this.referer = referer;
    }

    public String getUserAgent() {
        return userAgent;
    }

    public void setUserAgent(String userAgent) {
        this.userAgent = userAgent;
    }
}