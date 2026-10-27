package com.sdsi.splitter.core;

import com.sdsi.splitter.model.Settlement;
import com.sdsi.splitter.model.SettlementPlan;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * Turns net balances into the fewest "A pays B ₹X" transfers (M3).
 *
 * <p><b>Why this is not just greedy.</b> Each transfer can settle at most one person completely, except
 * the last transfer inside a group of people whose balances cancel out, which settles two. So if the
 * people with a non-zero balance can be split into at most k separate zero-sum groups, the minimum is
 * {@code (people with non-zero balance) - k}. Finding the largest k is NP-hard in general. Greedy
 * "largest debtor pays largest creditor" ignores it and can use more transfers than needed.
 *
 * <p><b>Algorithm.</b>
 * <ul>
 *   <li>Up to {@value #EXACT_LIMIT} people with non-zero balances: exact dynamic programming over subsets
 *       (O(2^n · n)) finds the largest k. Each zero-sum group is then settled greedily, which takes at
 *       most size-1 transfers. The result is <em>proven minimal</em>.</li>
 *   <li>Larger groups: greedy matching with heaps, O(n log n), at most n-1 transfers ("near-minimal").</li>
 * </ul>
 */
public final class DebtSimplifier {

    /** 2^20 subsets is about 1M states: well under a second and about 12 MB of arrays. */
    public static final int EXACT_LIMIT = 20;

    private DebtSimplifier() {
    }

    /**
     * @param balances member -> net paise (positive = gets money back). Must sum to zero.
     */
    public static SettlementPlan simplify(Map<String, Long> balances) {
        List<String> names = new ArrayList<>();
        List<Long> amounts = new ArrayList<>();
        long total = 0;
        for (Map.Entry<String, Long> e : balances.entrySet()) {
            total += e.getValue();
            if (e.getValue() != 0) {
                names.add(e.getKey());
                amounts.add(e.getValue());
            }
        }
        if (total != 0) {
            throw new IllegalArgumentException("balances must sum to zero, got " + total);
        }
        if (names.isEmpty()) {
            return new SettlementPlan(List.of(), true);
        }
        if (names.size() > EXACT_LIMIT) {
            Map<String, Long> all = new LinkedHashMap<>();
            for (int i = 0; i < names.size(); i++) {
                all.put(names.get(i), amounts.get(i));
            }
            return new SettlementPlan(sorted(greedy(all)), false);
        }

        List<Settlement> out = new ArrayList<>();
        for (List<Integer> group : maxZeroSumPartition(amounts)) {
            Map<String, Long> sub = new LinkedHashMap<>();
            for (int i : group) {
                sub.put(names.get(i), amounts.get(i));
            }
            out.addAll(greedy(sub));
        }
        return new SettlementPlan(sorted(out), true);
    }

    /**
     * Splits the indices into as many zero-sum groups as possible.
     *
     * <p>{@code dp[mask]} = the most zero-sum groups the people in {@code mask} can be split into when they
     * are added one by one. A group ends each time the running total returns to zero.
     */
    static List<List<Integer>> maxZeroSumPartition(List<Long> amounts) {
        int n = amounts.size();
        int full = (1 << n) - 1;
        long[] sum = new long[1 << n];
        int[] dp = new int[1 << n];
        for (int mask = 1; mask <= full; mask++) {
            int low = Integer.numberOfTrailingZeros(mask);
            sum[mask] = sum[mask & (mask - 1)] + amounts.get(low);
            int best = 0;
            for (int rest = mask; rest != 0; rest &= rest - 1) {
                int bit = rest & -rest;
                best = Math.max(best, dp[mask ^ bit]);
            }
            dp[mask] = best + (sum[mask] == 0 ? 1 : 0);
        }

        // Walk back from the full set to recover one order of adding people that achieves dp[full].
        int[] order = new int[n];
        int mask = full;
        for (int pos = n - 1; pos >= 0; pos--) {
            int need = dp[mask] - (sum[mask] == 0 ? 1 : 0);
            for (int rest = mask; rest != 0; rest &= rest - 1) {
                int bit = rest & -rest;
                if (dp[mask ^ bit] == need) {
                    order[pos] = Integer.numberOfTrailingZeros(bit);
                    mask ^= bit;
                    break;
                }
            }
        }

        List<List<Integer>> groups = new ArrayList<>();
        List<Integer> current = new ArrayList<>();
        long running = 0;
        for (int idx : order) {
            current.add(idx);
            running += amounts.get(idx);
            if (running == 0) {
                groups.add(current);
                current = new ArrayList<>();
            }
        }
        return groups;
    }

    /**
     * Largest debtor pays largest creditor until everyone is settled. Each transfer fully settles at least
     * one person, so this uses at most (people - 1) transfers. Public so the exact algorithm can be
     * compared against it.
     */
    public static List<Settlement> greedy(Map<String, Long> balances) {
        Comparator<Map.Entry<String, Long>> byAmountThenName =
                Map.Entry.<String, Long>comparingByValue().reversed().thenComparing(Map.Entry.comparingByKey());
        PriorityQueue<Map.Entry<String, Long>> creditors = new PriorityQueue<>(byAmountThenName);
        PriorityQueue<Map.Entry<String, Long>> debtors = new PriorityQueue<>(byAmountThenName);
        balances.forEach((name, net) -> {
            if (net > 0) {
                creditors.add(Map.entry(name, net));
            } else if (net < 0) {
                debtors.add(Map.entry(name, -net));
            }
        });

        List<Settlement> out = new ArrayList<>();
        while (!creditors.isEmpty() && !debtors.isEmpty()) {
            Map.Entry<String, Long> c = creditors.poll();
            Map.Entry<String, Long> d = debtors.poll();
            long pay = Math.min(c.getValue(), d.getValue());
            out.add(new Settlement(d.getKey(), c.getKey(), pay));
            if (c.getValue() > pay) {
                creditors.add(Map.entry(c.getKey(), c.getValue() - pay));
            }
            if (d.getValue() > pay) {
                debtors.add(Map.entry(d.getKey(), d.getValue() - pay));
            }
        }
        return out;
    }

    private static List<Settlement> sorted(List<Settlement> list) {
        List<Settlement> copy = new ArrayList<>(list);
        copy.sort(Comparator.comparing(Settlement::from).thenComparing(Settlement::to));
        return List.copyOf(copy);
    }
}
