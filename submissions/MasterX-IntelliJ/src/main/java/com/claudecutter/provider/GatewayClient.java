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
 * Client for the Anthropic-Messages-format gateway (probe-confirmed).
 * Posts to {@code {baseUrl}/v1/messages} with {@code Authorization: Bearer}
 * + {@code anthropic-version}, parses text blocks and usage directly — no
 * SDK, so it tolerates the gateway's non-standard extra fields.
 *
 * <p>Credentials come from env, never hardcoded:
 * {@code ANTHROPIC_BASE_URL} + {@code ANTHROPIC_AUTH_TOKEN} (or {@code ANTHROPIC_API_KEY}).
 */
public final class GatewayClient implements LlmClient {

    private final String authToken;
    private final String baseUrl;
    private final String model;
    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30)).build();
    private final ObjectMapper json = new ObjectMapper();

    public GatewayClient(String baseUrl, String authToken, String model) {
        this.baseUrl = stripTrailingSlash(baseUrl);
        this.authToken = authToken;
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
        body.put("max_tokens", 4096);
        if (system != null && !system.isBlank()) {
            body.put("system", system);
        }
        ArrayNode messages = body.putArray("messages");
        ObjectNode usr = messages.addObject();
        usr.put("role", "user");
        usr.put("content", user);

        String url = baseUrl + "/v1/messages";
        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(180))
                    .header("Authorization", "Bearer " + authToken)
                    .header("anthropic-version", "2023-06-01")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body)))
                    .build();

            HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                throw new IllegalStateException("Gateway HTTP " + resp.statusCode()
                        + " from " + url + ": " + truncate(resp.body(), 500));
            }

            JsonNode root = json.readTree(resp.body());
            StringBuilder text = new StringBuilder();
            JsonNode content = root.path("content");
            if (content.isArray()) {
                for (JsonNode block : content) {
                    if ("text".equals(block.path("type").asText())) {
                        text.append(block.path("text").asText()).append("\n");
                    }
                }
            }
            JsonNode usage = root.path("usage");
            long in = usage.path("input_tokens").asLong(0);
            long out = usage.path("output_tokens").asLong(0);
            long cacheRead = usage.path("cache_read_input_tokens").asLong(0);
            return new LlmResponse(text.toString().trim(), new ModelUsage(model, in, out, cacheRead, 0));
        } catch (Exception e) {
            throw new RuntimeException("Gateway call failed for " + url + ": " + e.getMessage(), e);
        }
    }

    private static String stripTrailingSlash(String s) {
        return s != null && s.endsWith("/") ? s.substring(0, s.length() - 1) : s;
    }

    private static String truncate(String s, int n) {
        return s == null ? "" : (s.length() <= n ? s : s.substring(0, n));
    }
}
