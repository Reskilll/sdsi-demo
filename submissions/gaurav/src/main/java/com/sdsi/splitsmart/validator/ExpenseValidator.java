package com.sdsi.splitsmart.validator;

import com.sdsi.splitsmart.dto.ExpenseRequest;
import com.sdsi.splitsmart.model.SplitType;

import java.util.Map;

/**
 * Validates business rules: % sum = 100, exact shares sum == total,
 * payer is in the member list.  (M5)
 */
public final class ExpenseValidator {

    private ExpenseValidator() {}

    /**
     * @throws IllegalArgumentException when any rule fails
     */
    public static void validate(ExpenseRequest req) {
        if (req.members() == null || !req.members().contains(req.payer())) {
            throw new IllegalArgumentException(
                    "payer '" + req.payer() + "' must be in the members list");
        }

        if (req.splitType() == SplitType.PERCENTAGE) {
            Map<String, Double> shares = req.shares();
            if (shares == null || shares.isEmpty()) {
                throw new IllegalArgumentException(
                        "PERCENTAGE split requires a 'shares' map with % per member");
            }
            double sum = shares.values().stream().mapToDouble(Double::doubleValue).sum();
            if (Math.abs(sum - 100.0) > 0.001) {
                throw new IllegalArgumentException(
                        "Percentages must sum to 100, got " + sum);
            }
            for (String m : req.members()) {
                if (!shares.containsKey(m)) {
                    throw new IllegalArgumentException(
                            "Member '" + m + "' missing from percentage shares");
                }
            }
        }

        if (req.splitType() == SplitType.EXACT) {
            Map<String, Double> shares = req.shares();
            if (shares == null || shares.isEmpty()) {
                throw new IllegalArgumentException(
                        "EXACT split requires a 'shares' map with ₹ per member");
            }
            double sum = shares.values().stream().mapToDouble(Double::doubleValue).sum();
            if (Math.abs(sum - req.amount()) > 0.001) {
                throw new IllegalArgumentException(
                        "Exact shares (₹" + sum + ") must equal total amount (₹" + req.amount() + ")");
            }
            for (String m : req.members()) {
                if (!shares.containsKey(m)) {
                    throw new IllegalArgumentException(
                            "Member '" + m + "' missing from exact shares");
                }
            }
        }
    }
}