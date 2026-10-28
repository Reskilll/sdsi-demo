package com.claudecutter.demo;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Probes the configured gateway to determine which request format it speaks.
 * Reads credentials from the environment (never hardcoded, never printed).
 * Safe to run repeatedly.
 */
public final class GatewayProbe {

    public static void main(String[] args) throws Exception {
        String base = System.getenv("ANTHROPIC_BASE_URL");
        String token = firstNonBlank(
                System.getenv("ANTHROPIC_AUTH_TOKEN"),
                System.getenv("ANTHROPIC_API_KEY"));

        System.out.println("baseUrl  : " + (base == null ? "(not set)" : base));
        System.out.println("token    : " + (token == null ? "(not set)" : "present (len " + token.length() + ")"));
        if (base == null || token == null) {
            System.out.println("Cannot probe: base URL and token both required.");
            return;
        }
        String b = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        String model = "deepseek/deepseek-v4-pro";

        probe("OpenAI /chat/completions", b + "/chat/completions", token, model,
                "{\"model\":\"" + model + "\",\"temperature\":0,\"messages\":["
                        + "{\"role\":\"user\",\"content\":\"Reply with exactly: pong\"}],\"max_tokens\":20}");
        probe("Anthropic /v1/messages", b + "/v1/messages", token, model,
                "{\"model\":\"" + model + "\",\"max_tokens\":20,\"messages\":["
                        + "{\"role\":\"user\",\"content\":\"Reply with exactly: pong\"}]}");
    }

    private static void probe(String label, String url, String token, String model, String body) {
        System.out.println("\n=== " + label + " ===");
        System.out.println("url: " + url);
        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(30))
                    .header("Authorization", "Bearer " + token)
                    .header("x-api-key", token)
                    .header("anthropic-version", "2023-06-01")
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> resp = HttpClient.newHttpClient().send(req, HttpResponse.BodyHandlers.ofString());
            System.out.println("HTTP " + resp.statusCode());
            System.out.println(truncate(resp.body(), 600));
        } catch (Exception e) {
            System.out.println("ERROR: " + e.getClass().getSimpleName() + " — " + e.getMessage());
        }
    }

    private static String firstNonBlank(String... vals) {
        for (String v : vals) {
            if (v != null && !v.isBlank()) {
                return v;
            }
        }
        return null;
    }

    private static String truncate(String s, int n) {
        return s == null ? "(empty)" : (s.length() <= n ? s : s.substring(0, n) + "...");
    }
}
