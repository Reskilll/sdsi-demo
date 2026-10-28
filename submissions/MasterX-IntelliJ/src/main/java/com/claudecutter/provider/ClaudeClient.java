package com.claudecutter.provider;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.claudecutter.model.ModelUsage;

/** Claude via the official Anthropic Java SDK. Defaults to the Opus tier. */
public final class ClaudeClient implements LlmClient {

    private final AnthropicClient client;
    private final String model;

    public ClaudeClient(String apiKey, String model) {
        this(AnthropicOkHttpClient.builder().apiKey(apiKey).build(), model);
    }

    public ClaudeClient(AnthropicClient client, String model) {
        this.client = client;
        this.model = model;
    }

    @Override
    public String model() {
        return model;
    }

    @Override
    public LlmResponse complete(String system, String user) {
        MessageCreateParams params = MessageCreateParams.builder()
                .model(model)
                .maxTokens(16000L)
                .system(system)
                .addUserMessage(user)
                .build();

        Message resp = client.messages().create(params);
        String text = resp.content().stream()
                .flatMap(block -> block.text().stream())
                .map(t -> t.text())
                .reduce((a, b) -> a + "\n" + b)
                .orElse("");

        var usage = resp.usage();
        ModelUsage mu = new ModelUsage(
                model,
                usage.inputTokens(),
                usage.outputTokens(),
                usage.cacheReadInputTokens().orElse(0L),
                usage.cacheCreationInputTokens().orElse(0L));
        return new LlmResponse(text, mu);
    }
}
