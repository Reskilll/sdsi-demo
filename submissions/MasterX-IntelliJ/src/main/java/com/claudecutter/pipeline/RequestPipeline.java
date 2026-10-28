package com.claudecutter.pipeline;

import com.claudecutter.accounting.TokenLedger;
import com.claudecutter.model.ModelUsage;
import com.claudecutter.model.RouteDecision;
import com.claudecutter.model.UsageRecord;
import com.claudecutter.provider.LlmClient;
import com.claudecutter.provider.LlmResponse;
import com.claudecutter.provider.TokenCounter;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Route -> (locate -> compress -> Claude) with per-request cost accounting.
 *
 * <p>The cheap model (Qwen) never writes the plan Claude follows — it shrinks what
 * Claude reads: routing the trivial away entirely, and compressing the complex.
 */
public final class RequestPipeline {

    private final LlmClient cheap;                  // Qwen
    private final LlmClient strong;                 // Claude
    private final Map<String, String> fileIndex;    // path -> content
    private final TokenLedger ledger;
    private final TokenCounter counter;
    private final ObjectMapper json = new ObjectMapper();
    private volatile StageListener listener;

    /** Receives stage transitions so a UI can show the worker/master handoff. */
    @FunctionalInterface
    public interface StageListener {
        void onStage(String stage);
    }

    public RequestPipeline(LlmClient cheap, LlmClient strong,
                           Map<String, String> fileIndex, TokenLedger ledger,
                           TokenCounter counter) {
        this.cheap = cheap;
        this.strong = strong;
        this.fileIndex = fileIndex;
        this.ledger = ledger;
        this.counter = counter;
    }

    public void setStageListener(StageListener listener) {
        this.listener = listener;
    }

    private void stage(String s) {
        StageListener l = listener;
        if (l != null) {
            l.onStage(s);
        }
    }

    /** Runs one user request end-to-end and logs it. */
    public String handle(String sessionId, String prompt) {
        UsageAccumulator qwenAcc = new UsageAccumulator(cheap.model());

        stage("Qwen (worker) is routing the request…");
        RouteDecision route = classify(prompt, qwenAcc);
        String answer;
        UsageRecord record;

        if (route.complexity() == RouteDecision.Complexity.TRIVIAL) {
            stage("Qwen (worker) is answering…");
            LlmResponse r = cheap.complete(assistantSystem(), prompt);
            qwenAcc.add(r.usage());
            answer = r.text();
            // Trivial baseline: what Claude alone would have cost = at least reading
            // the prompt (no file context needed). Claude never runs, so claudeUsage is null.
            record = new UsageRecord(Instant.now(), sessionId, prompt, route, List.of(),
                    counter.count(prompt), 0, qwenAcc.sum(), null);
        } else {
            stage("Qwen (worker) is locating relevant files…");
            List<String> files = locate(prompt, qwenAcc);
            String contents = read(files);
            stage("Qwen (worker) is compressing context…");
            LlmResponse spec = cheap.complete(Prompts.compressorSystem(),
                    Prompts.compressorUser(prompt, contents));
            qwenAcc.add(spec.usage());

            long full = counter.count(contents);
            stage("Claude (master) is answering…");
            LlmResponse out = strong.complete(assistantSystem(),
                    prompt + "\n\nRelevant code (compressed):\n" + spec.text());
            answer = out.text();

            record = new UsageRecord(Instant.now(), sessionId, prompt, route, files,
                    full, counter.count(spec.text()), qwenAcc.sum(), out.usage());
        }

        stage("");
        ledger.record(record);
        return answer;
    }

    private RouteDecision classify(String prompt, UsageAccumulator acc) {
        // Deterministic pre-gate: obvious code-generation requests never go to the
        // cheap model — they are exactly the "small coding task → compress → Claude"
        // case the product exists for.
        RouteDecision gated = keywordGate(prompt);
        if (gated != null) {
            return gated;
        }

        LlmResponse r = cheap.complete(Prompts.routerSystem(), Prompts.routerUser(prompt));
        acc.add(r.usage());
        try {
            JsonNode node = json.readTree(extractJson(r.text()));
            boolean complex = "complex".equalsIgnoreCase(node.path("complexity").asText());
            String reason = node.path("reason").asText("");
            return new RouteDecision(
                    complex ? RouteDecision.Complexity.COMPLEX : RouteDecision.Complexity.TRIVIAL,
                    reason);
        } catch (Exception e) {
            // If the cheap model returns garbage, default to COMPLEX (route to Claude)
            // rather than silently answering a hard request with Qwen.
            return new RouteDecision(RouteDecision.Complexity.COMPLEX, "unparseable -> claude");
        }
    }

    private static RouteDecision keywordGate(String prompt) {
        String p = " " + prompt.toLowerCase() + " ";
        String[] complex = {
            "write", "generate", "build", "create", "make", "implement", "code for",
            "code to", "add a", "add retry", "fix the bug", "refactor", "feature",
            "script for", "program for", "page for", "page using", "function to",
            "class for", "api for", "endpoint"
        };
        for (String k : complex) {
            if (p.contains(k)) {
                return new RouteDecision(RouteDecision.Complexity.COMPLEX, "code-generation keyword: " + k);
            }
        }
        return null;
    }

    private List<String> locate(String prompt, UsageAccumulator acc) {
        LlmResponse r = cheap.complete(Prompts.locatorSystem(),
                Prompts.locatorUser(prompt, new ArrayList<>(fileIndex.keySet())));
        acc.add(r.usage());
        try {
            JsonNode node = json.readTree(extractJson(r.text()));
            List<String> paths = new ArrayList<>();
            if (node.isArray()) {
                node.forEach(n -> {
                    String p = n.asText();
                    if (fileIndex.containsKey(p)) {
                        paths.add(p);
                    }
                });
            }
            return paths;
        } catch (Exception e) {
            return List.of();
        }
    }

    private String read(List<String> files) {
        StringBuilder sb = new StringBuilder();
        for (String f : files) {
            sb.append("### ").append(f).append("\n");
            sb.append(fileIndex.get(f)).append("\n\n");
        }
        return sb.toString();
    }

    private static String assistantSystem() {
        return "You are a senior software engineer. Answer the request using the provided context.";
    }

    private static String extractJson(String raw) {
        String s = raw.trim().replaceAll("(?s)```(?:json)?\\s*(.*?)\\s*```", "$1").trim();
        int brace = s.indexOf('{');
        int bracket = s.indexOf('[');
        int start;
        if (brace == -1) {
            start = bracket;
        } else if (bracket == -1) {
            start = brace;
        } else {
            start = Math.min(brace, bracket);
        }
        return start == -1 ? s : s.substring(start).trim();
    }

    private static final class UsageAccumulator {
        private final String model;
        private long in;
        private long out;

        UsageAccumulator(String model) {
            this.model = model;
        }

        void add(ModelUsage u) {
            if (u == null) {
                return;
            }
            in += u.inputTokens();
            out += u.outputTokens();
        }

        ModelUsage sum() {
            return new ModelUsage(model, in, out, 0, 0);
        }
    }
}
