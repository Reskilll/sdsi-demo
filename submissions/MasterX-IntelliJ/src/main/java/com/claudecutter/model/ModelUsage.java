package com.claudecutter.model;

/**
 * Measured token usage for a single model call, straight from the provider's
 * {@code usage} object. All fields are absolute (factual), never estimated.
 */
public record ModelUsage(
        String model,
        long inputTokens,
        long outputTokens,
        long cacheReadTokens,
        long cacheWriteTokens) {

    public long totalTokens() {
        return inputTokens + outputTokens + cacheReadTokens + cacheWriteTokens;
    }
}
