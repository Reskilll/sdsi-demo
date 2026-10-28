package com.claudecutter.provider;

/**
 * Tries the primary client; on any failure, transparently falls back to the
 * secondary. Lets the gateway be attempted without ever breaking the demo —
 * if the gateway is unreachable or misconfigured, the caller still gets an
 * answer (from the fallback) instead of an exception.
 */
public final class FallbackLlmClient implements LlmClient {

    private final LlmClient primary;
    private final LlmClient fallback;

    public FallbackLlmClient(LlmClient primary, LlmClient fallback) {
        this.primary = primary;
        this.fallback = fallback;
    }

    @Override
    public String model() {
        return primary.model();
    }

    @Override
    public LlmResponse complete(String system, String user) {
        try {
            return primary.complete(system, user);
        } catch (RuntimeException e) {
            return fallback.complete(system, user);
        }
    }
}
