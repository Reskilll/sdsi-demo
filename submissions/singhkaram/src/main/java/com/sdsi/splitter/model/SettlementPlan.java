package com.sdsi.splitter.model;

import java.util.List;

/**
 * @param optimal true when the plan is proven to have the fewest possible transfers; false when the
 *                greedy fallback was used for a very large group (at most n-1 transfers)
 */
public record SettlementPlan(List<Settlement> settlements, boolean optimal) {
}
