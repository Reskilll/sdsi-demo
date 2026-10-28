package com.claudecutter.cost;

import com.claudecutter.model.ModelUsage;
import com.claudecutter.model.Pricing;
import com.claudecutter.model.UsageRecord;

public final class CostCalculator {

    public record CostBreakdown(
            double qwenCostUsd,
            double claudeCostUsd,
            double totalCostUsd,
            double baselineCostUsd,
            double savingsUsd,
            double savingsPct) {

        @Override
        public String toString() {
            return String.format(
                    "qwen=$%.4f claude=$%.4f total=$%.4f | baseline=$%.4f saved=$%.4f (%.1f%%)",
                    qwenCostUsd, claudeCostUsd, totalCostUsd,
                    baselineCostUsd, savingsUsd, savingsPct);
        }
    }

    private CostCalculator() {}

    /** Cost of a single model call, from measured usage. */
    public static double costOf(ModelUsage u, Pricing pricing) {
        if (u == null) {
            return 0.0;
        }
        Pricing.Rate r = pricing.require(u.model());
        return (r.input() * u.inputTokens()
                + r.output() * u.outputTokens()
                + r.cacheRead() * u.cacheReadTokens()
                + r.input() * u.cacheWriteTokens()) / 1_000_000.0;
    }

    /**
     * Baseline = what Claude alone would have cost reading the full
     * (uncompressed) context and producing the same output. This is a
     * counterfactual, so the UI must label it as an estimate.
     */
    public static CostBreakdown compute(UsageRecord rec, Pricing pricing) {
        double qwen = costOf(rec.qwenUsage(), pricing);
        double claude = costOf(rec.claudeUsage(), pricing);
        double total = qwen + claude;

        ModelUsage c = rec.claudeUsage();
        String model = c != null ? c.model() : "claude-opus-5-5";
        Pricing.Rate r = pricing.require(model);
        double baseline = (r.input() * rec.fullContextTokensEst()
                + r.output() * (c != null ? c.outputTokens() : 0)) / 1_000_000.0;

        double savings = baseline - total;
        double pct = baseline > 0 ? savings / baseline * 100.0 : 0.0;
        return new CostBreakdown(qwen, claude, total, baseline, savings, pct);
    }
}
