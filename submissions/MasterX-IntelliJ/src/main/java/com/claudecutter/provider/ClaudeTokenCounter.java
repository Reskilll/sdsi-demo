package com.claudecutter.provider;

import com.anthropic.client.AnthropicClient;
import com.anthropic.models.messages.MessageCountTokensParams;

/**
 * Accurate token counts via Claude's {@code count_tokens} endpoint.
 *
 * <p>Token counts are model-specific — always count against the same model you
 * will run inference on. This is the correct tool; do not use tiktoken or a
 * chars/4 guess for real savings numbers.
 */
public final class ClaudeTokenCounter implements TokenCounter {

    private final AnthropicClient client;
    private final String model;

    public ClaudeTokenCounter(AnthropicClient client, String model) {
        this.client = client;
        this.model = model;
    }

    @Override
    public long count(String text) {
        if (text == null || text.isEmpty()) {
            return 0;
        }
        long tokens = client.messages().countTokens(
                MessageCountTokensParams.builder()
                        .model(model)
                        .addUserMessage(text)
                        .build()
        ).inputTokens();
        return Math.max(1, tokens);
    }
}
