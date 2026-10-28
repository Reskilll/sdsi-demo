package com.claudecutter.model;

import java.time.Instant;
import java.util.List;

/**
 * One logged request — the row the dashboard reads.
 *
 * <p>Deliberately splits <em>measured</em> from <em>estimated</em> numbers so the
 * UI never blurs them:
 * <ul>
 *   <li>measured: {@link #qwenUsage()}, {@link #claudeUsage()} — from the API.</li>
 *   <li>estimated: {@link #fullContextTokensEst()} — the counterfactual "what
 *       Claude would have read without us", modeled from the located files.</li>
 * </ul>
 */
public record UsageRecord(
        Instant timestamp,
        String sessionId,
        String prompt,
        RouteDecision route,
        List<String> locatedFiles,
        long fullContextTokensEst,
        long compressedContextTokens,
        ModelUsage qwenUsage,
        ModelUsage claudeUsage) {

    /** True if Claude never touched this request (trivial route). */
    public boolean routedAwayFromClaude() {
        return claudeUsage == null || claudeUsage.totalTokens() == 0;
    }
}
