package com.claudecutter.provider;

/**
 * Rough fallback (chars/4) for when no live Claude client is available
 * (offline demo, tests). NOT accurate — undercounts code by ~15-20%.
 * Use {@link ClaudeTokenCounter} for any number the user will trust.
 */
public final class CharTokenCounter implements TokenCounter {

    @Override
    public long count(String text) {
        return text == null || text.isEmpty() ? 0 : Math.max(1, text.length() / 4);
    }
}
