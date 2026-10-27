package com.sdsi.splitter.model;

import java.util.Map;

/**
 * A validated expense. {@code shares} maps each participant to what they owe, in paise, and always sums
 * to {@code amountPaise} exactly.
 */
public record Expense(String id, String description, String paidBy, long amountPaise, SplitType split,
                      Map<String, Long> shares) {
}
