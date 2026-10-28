package com.claudecutter.demo;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.claudecutter.accounting.TokenLedger;
import com.claudecutter.dashboard.DashboardExporter;
import com.claudecutter.model.Pricing;
import com.claudecutter.pipeline.RequestPipeline;
import com.claudecutter.provider.CharTokenCounter;
import com.claudecutter.provider.ClaudeClient;
import com.claudecutter.provider.ClaudeTokenCounter;
import com.claudecutter.provider.FallbackLlmClient;
import com.claudecutter.provider.GatewayClient;
import com.claudecutter.provider.LlmClient;
import com.claudecutter.provider.QwenClient;
import com.claudecutter.provider.TokenCounter;

import java.nio.file.Path;
import java.util.Map;

/** Runs the pipeline end-to-end and writes the dashboard. */
public final class DemoApp {

    public static void main(String[] args) {
        Pricing pricing = new Pricing();
        TokenLedger ledger = new TokenLedger(pricing);
        Map<String, String> fileIndex = SampleCodebase.build();

        Providers providers = providers();
        RequestPipeline pipeline = new RequestPipeline(
                providers.qwen, providers.claude, fileIndex, ledger, providers.counter);

        System.out.println("\n--- trivial request ---");
        System.out.println(pipeline.handle("s1", "What does OrderService.checkout do?"));

        System.out.println("\n--- complex request ---");
        System.out.println(pipeline.handle("s1", "Add retry logic to the checkout payment flow"));

        System.out.println("\n--- dashboard ---");
        System.out.println(ledger.summary());

        Path out = Path.of("dashboard.html");
        new DashboardExporter(ledger, pricing).export(out);
        System.out.println("\nDashboard written to: " + out.toAbsolutePath());
    }

    /** Resolves clients: gateway (fail-safe) -> real Anthropic+Qwen -> mocks. */
    static Providers providers() {
        // 1) The Claude Code gateway (Anthropic Messages format, probe-confirmed).
        String gatewayUrl = System.getenv("ANTHROPIC_BASE_URL");
        String gatewayToken = firstNonBlank(
                System.getenv("ANTHROPIC_AUTH_TOKEN"),
                System.getenv("ANTHROPIC_API_KEY"));
        if (gatewayUrl != null && !gatewayUrl.isBlank() && gatewayToken != null && !gatewayToken.isBlank()) {
            System.out.println("== using gateway provider: " + gatewayUrl + " ==");
            LlmClient cheap = new FallbackLlmClient(
                    new GatewayClient(gatewayUrl, gatewayToken, "deepseek/deepseek-v4-flash"),
                    new MockLlmClient("deepseek/deepseek-v4-flash", 50, 40));
            LlmClient strong = new FallbackLlmClient(
                    new GatewayClient(gatewayUrl, gatewayToken, "deepseek/deepseek-v4-pro"),
                    new MockLlmClient("deepseek/deepseek-v4-pro", 150, 800));
            return new Providers(cheap, strong, new CharTokenCounter());
        }

        // 2) Real Anthropic + DashScope (Qwen).
        String dash = System.getenv("DASHSCOPE_API_KEY");
        String ant = System.getenv("ANTHROPIC_API_KEY");
        if (dash != null && !dash.isBlank() && ant != null && !ant.isBlank()) {
            AnthropicClient anthropic = AnthropicOkHttpClient.builder().apiKey(ant).build();
            System.out.println("== using real providers (Anthropic + Qwen) ==");
            return new Providers(
                    new QwenClient(dash,
                            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                            "qwen-plus"),
                    new ClaudeClient(anthropic, "claude-opus-5-5"),
                    new ClaudeTokenCounter(anthropic, "claude-opus-5-5"));
        }

        // 3) Offline fallback.
        System.out.println("== no API keys found; using mock clients (offline demo) ==");
        return new Providers(
                new MockLlmClient("qwen-turbo", 50, 40),
                new MockLlmClient("claude-opus-5-5", 150, 800),
                new CharTokenCounter());
    }

    private static String firstNonBlank(String... values) {
        for (String v : values) {
            if (v != null && !v.isBlank()) {
                return v;
            }
        }
        return null;
    }

    record Providers(LlmClient qwen, LlmClient claude, TokenCounter counter) {}
}
