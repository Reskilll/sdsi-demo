package com.urlshortener.dto;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public class ShortenRequest {

    @jakarta.validation.constraints.NotBlank(message = "URL must not be blank")
    @Size(max = 2048, message = "URL must not exceed 2048 characters")
    private String url;

    @Size(min = 4, max = 20, message = "Custom alias must be between 4 and 20 characters")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$", message = "Custom alias must contain only alphanumeric characters, hyphens, and underscores")
    private String customAlias;

    // Expiry in days from now. Null means no expiry.
    private Integer expiryDays;

    public ShortenRequest() {
    }

    public ShortenRequest(String url, String customAlias, Integer expiryDays) {
        this.url = url;
        this.customAlias = customAlias;
        this.expiryDays = expiryDays;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public String getCustomAlias() {
        return customAlias;
    }

    public void setCustomAlias(String customAlias) {
        this.customAlias = customAlias;
    }

    public Integer getExpiryDays() {
        return expiryDays;
    }

    public void setExpiryDays(Integer expiryDays) {
        this.expiryDays = expiryDays;
    }
}