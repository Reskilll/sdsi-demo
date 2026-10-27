package com.sdsi.splitter.model;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * Unvalidated expense as the user described it.
 *
 * @param id           optional; generated when null
 * @param participants for EQUAL splits; null means "all members"
 * @param shares       for EXACT (rupees) and PERCENTAGE (percent) splits, in input order
 */
public record ExpenseRequest(
        String id,
        String description,
        String paidBy,
        BigDecimal amount,
        SplitType split,
        List<String> participants,
        Map<String, BigDecimal> shares) {

    public static ExpenseRequest equal(String description, String paidBy, String amount, List<String> participants) {
        return new ExpenseRequest(null, description, paidBy, new BigDecimal(amount), SplitType.EQUAL, participants, null);
    }

    public static ExpenseRequest exact(String description, String paidBy, String amount, Map<String, BigDecimal> shares) {
        return new ExpenseRequest(null, description, paidBy, new BigDecimal(amount), SplitType.EXACT, null, shares);
    }

    public static ExpenseRequest percentage(String description, String paidBy, String amount, Map<String, BigDecimal> shares) {
        return new ExpenseRequest(null, description, paidBy, new BigDecimal(amount), SplitType.PERCENTAGE, null, shares);
    }
}
