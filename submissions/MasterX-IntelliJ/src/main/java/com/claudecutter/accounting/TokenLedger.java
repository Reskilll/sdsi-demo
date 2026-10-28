package com.claudecutter.accounting;

import com.claudecutter.cost.CostCalculator;
import com.claudecutter.model.Pricing;
import com.claudecutter.model.UsageRecord;

import java.util.ArrayList;
import java.util.List;

/** Accumulates usage records and produces the dashboard numbers. */
public final class TokenLedger {

    private final Pricing pricing;
    private final List<UsageRecord> records = new ArrayList<>();

    public TokenLedger(Pricing pricing) {
        this.pricing = pricing;
    }

    public void record(UsageRecord r) {
        records.add(r);
    }

    public List<UsageRecord> records() {
        return List.copyOf(records);
    }

    public Summary summary() {
        long qwenIn = 0, qwenOut = 0, claudeIn = 0, claudeOut = 0, cacheRead = 0;
        long baselineTokens = 0, compressedTokens = 0;
        int trivial = 0, complex = 0;

        for (UsageRecord r : records) {
            if (r.routedAwayFromClaude()) {
                trivial++;
            } else {
                complex++;
            }
            baselineTokens += r.fullContextTokensEst();
            compressedTokens += r.compressedContextTokens();
            if (r.qwenUsage() != null) {
                qwenIn += r.qwenUsage().inputTokens();
                qwenOut += r.qwenUsage().outputTokens();
            }
            if (r.claudeUsage() != null) {
                claudeIn += r.claudeUsage().inputTokens();
                claudeOut += r.claudeUsage().outputTokens();
                cacheRead += r.claudeUsage().cacheReadTokens();
            }
        }

        double totalCost = records.stream()
                .mapToDouble(r -> CostCalculator.compute(r, pricing).totalCostUsd()).sum();
        double baselineCost = records.stream()
                .mapToDouble(r -> CostCalculator.compute(r, pricing).baselineCostUsd()).sum();

        return new Summary(
                records.size(), trivial, complex,
                qwenIn, qwenOut, claudeIn, claudeOut, cacheRead,
                baselineTokens, compressedTokens,
                totalCost, baselineCost);
    }

    /** Dashboard-ready rollup. */
    public record Summary(
            int requests,
            int trivialRouted,
            int complexRouted,
            long qwenInputTokens,
            long qwenOutputTokens,
            long claudeInputTokens,
            long claudeOutputTokens,
            long claudeCacheReadTokens,
            long baselineContextTokens,
            long compressedContextTokens,
            double totalCostUsd,
            double baselineCostUsd) {

        public double savingsUsd() {
            return baselineCostUsd - totalCostUsd;
        }

        public double savingsPct() {
            return baselineCostUsd > 0 ? savingsUsd() / baselineCostUsd * 100.0 : 0.0;
        }

        public double contextReductionPct() {
            return baselineContextTokens > 0
                    ? (1.0 - (double) compressedContextTokens / baselineContextTokens) * 100.0
                    : 0.0;
        }

        @Override
        public String toString() {
            return String.format("""
                    Requests          : %d (%d trivial -> Qwen, %d complex -> Claude)
                    Context           : baseline %,d tok -> compressed %,d tok (%.1f%% cut)
                    Qwen tokens       : %,d in / %,d out
                    Claude tokens     : %,d in / %,d out (%,d cache-read)
                    Cost              : $%.4f actual vs $%.4f baseline
                    Savings           : $%.4f (%.1f%%)""",
                    requests, trivialRouted, complexRouted,
                    baselineContextTokens, compressedContextTokens, contextReductionPct(),
                    qwenInputTokens, qwenOutputTokens,
                    claudeInputTokens, claudeOutputTokens, claudeCacheReadTokens,
                    totalCostUsd, baselineCostUsd,
                    savingsUsd(), savingsPct());
        }
    }
}
