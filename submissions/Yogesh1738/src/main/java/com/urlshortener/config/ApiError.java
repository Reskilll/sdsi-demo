package com.urlshortener.config;

import java.time.Instant;
import java.util.Map;

/**
 * Standard error payload.
 */
public record ApiError(
    int status,
    String error,
    String message,
    String path,
    Instant timestamp,
    Map<String, String> fieldErrors
) {
    public static ApiError of(int status, String error, String message, String path) {
        return new ApiError(status, error, message, path, Instant.now(), null);
    }

    public static ApiError withFields(int status, String error, String message,
                                      String path, Map<String, String> fieldErrors) {
        return new ApiError(status, error, message, path, Instant.now(), fieldErrors);
    }
}