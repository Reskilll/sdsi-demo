package com.claudecutter.model;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * USD per million tokens, per model.
 *
 * <p>Claude rates are first-party Anthropic list prices. Qwen rates are
 * PLACEHOLDERS — fill in your DashScope / ModelStudio rates before trusting
 * any cost number that involves Qwen.
 */
public final class Pricing {

    public record Rate(double input, double output, double cacheRead) {
        public static Rate of(double input, double output, double cacheRead) {
            return new Rate(input, output, cacheRead);
        }

        public static Rate of(double input, double output) {
            return new Rate(input, output, 0.0);
        }
    }

    private final Map<String, Rate> rates = new HashMap<>();

    public Pricing() {
        // Claude (Anthropic list prices, USD / 1M tokens).
        rates.put("claude-opus-5-5", Rate.of(4.00, 20.00, 0.20));
        rates.put("claude-fable-5-1", Rate.of(10.00, 50.00, 0.00));
        rates.put("claude-sonnet-5-5", Rate.of(2.00, 10.00, 0.20));
        rates.put("claude-haiku-5-5", Rate.of(0.10, 0.50, 0.00));

        // Qwen — PLACEHOLDER. Replace with your provider's actual rates.
        rates.put("qwen-max", Rate.of(1.20, 6.00));
        rates.put("qwen-plus", Rate.of(0.40, 1.20));
        rates.put("qwen-turbo", Rate.of(0.15, 0.60));

        // Gateway model aliases — mapped onto the qwen/claude tiers so the
        // dashboard keeps its "qwen vs claude" framing regardless of the
        // underlying gateway model IDs.
        rates.put("deepseek/deepseek-v4-flash", Rate.of(0.15, 0.60));   // ~ qwen
        rates.put("deepseek/deepseek-v4-pro", Rate.of(4.00, 20.00, 0.20)); // ~ claude
    }

    public Pricing put(String model, Rate rate) {
        rates.put(model, rate);
        return this;
    }

    public Optional<Rate> rate(String model) {
        return Optional.ofNullable(rates.get(model));
    }

    public Rate require(String model) {
        return rate(model).orElseThrow(() ->
                new IllegalArgumentException("No price configured for model '" + model + "'"));
    }
}
