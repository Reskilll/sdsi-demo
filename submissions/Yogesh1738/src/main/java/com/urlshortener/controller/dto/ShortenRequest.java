package com.urlshortener.controller.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Request body for the "shorten" endpoint.
 */
public class ShortenRequest {

    @NotBlank(message = "url is required")
    private String url;

    private String customAlias;

    private Integer ttlMinutes;

    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }

    public String getCustomAlias() { return customAlias; }
    public void setCustomAlias(String customAlias) { this.customAlias = customAlias; }

    public Integer getTtlMinutes() { return ttlMinutes; }
    public void setTtlMinutes(Integer ttlMinutes) { this.ttlMinutes = ttlMinutes; }
}