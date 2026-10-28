package com.claudecutter.provider;

import com.claudecutter.model.ModelUsage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Qwen via its OpenAI-compatible endpoint (DashScope / ModelStudio).
 * Configure {@code baseUrl} + {@code model} for whichever Qwen deployment you use.
 */
public final class QwenClient implements LlmClient {

    private final String apiKey;
    private final String baseUrl;
    private final String model;
    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30)).build();
    private final ObjectMapper json = new ObjectMapper();

    public QwenClient(String apiKey, String baseUrl, String model) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.model = model;
    }

    @Override
    public String model() {
        return model;
    }

    @Override
    public LlmResponse complete(String system, String user) {
        ObjectNode body = json.createObjectNode();
        body.put("model", model);
        body.put("temperature", 0.0);
        ArrayNode messages = body.putArray("messages");
        ObjectNode sys = messages.addObject();
        sys.put("role", "system");
        sys.put("content", system);
        ObjectNode usr = messages.addObject();
        usr.put("role", "user");
        usr.put("content", user);

        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl))
                    .timeout(Duration.ofSeconds(120))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body)))
                    .build();

            HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                throw new IllegalStateException("Qwen HTTP " + resp.statusCode() + ": " + resp.body());
            }

            JsonNode root = json.readTree(resp.body());
            String text = root.at("/choices/0/message/content").asText("");
            JsonNode usage = root.path("usage");
            long in = usage.has("prompt_tokens")
                    ? usage.path("prompt_tokens").asLong()
                    : usage.path("input_tokens").asLong(0);
            long out = usage.has("completion_tokens")
                    ? usage.path("completion_tokens").asLong()
                    : usage.path("output_tokens").asLong(0);
            return new LlmResponse(text, new ModelUsage(model, in, out, 0, 0));
        } catch (Exception e) {
            throw new RuntimeException("Qwen call failed", e);
        }
    }
}
