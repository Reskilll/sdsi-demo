package com.claudecutter.demo;

import com.claudecutter.provider.CharTokenCounter;
import com.claudecutter.provider.FallbackLlmClient;
import com.claudecutter.provider.GatewayClient;
import com.claudecutter.provider.LlmClient;
import com.claudecutter.provider.TokenCounter;

import javax.swing.SwingUtilities;
import javax.swing.UIManager;

/**
 * Standalone entry point that drives the chat with the live gateway
 * (probe-confirmed Anthropic Messages format at {@code ANTHROPIC_BASE_URL}).
 *
 * <p>Reads credentials from env only — {@code ANTHROPIC_BASE_URL} +
 * {@code ANTHROPIC_AUTH_TOKEN} (or {@code ANTHROPIC_API_KEY}) — and never
 * hardcodes them. Each role has a mock fallback, so if the gateway is down the
 * chat still answers instead of erroring.
 *
 * <p>Run with: {@code mvn -q -DskipTests compile exec:java -Dexec.mainClass=com.claudecutter.demo.GatewayChat}
 */
public final class GatewayChat {

    public static void main(String[] args) throws Exception {
        UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        DemoApp.Providers providers = DemoApp.providers();
        boolean live = !providers.qwen().model().contains("turbo");
        ChatDemo demo = new ChatDemo(providers.qwen(), providers.claude(), providers.counter(), live);
        SwingUtilities.invokeLater(demo::build);
    }
}
