package com.sdsi.splitsmart.model;

import java.util.List;
import java.util.Map;

/**
 * Immutable record of a single expense.
 *
 * @param payer     who paid
 * @param amount    total expense amount in ₹
 * @param splitType EQUAL | EXACT | PERCENTAGE
 * @param members   everyone involved in this expense (including payer)
 * @param shares    member → share (₹ for EXACT, % for PERCENTAGE, unused for EQUAL)
 */
public record Expense(
        String payer,
        double amount,
        SplitType splitType,
        List<String> members,
        Map<String, Double> shares
) {
    public Expense {
        members = members != null ? List.copyOf(members) : List.of();
        shares = shares != null ? Map.copyOf(shares) : Map.of();
    }
}