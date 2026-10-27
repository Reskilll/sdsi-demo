package com.sdsi.splitter;

import com.sdsi.splitter.core.DebtSimplifier;
import com.sdsi.splitter.model.Settlement;
import com.sdsi.splitter.model.SettlementPlan;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DebtSimplifierTest {

    private static Map<String, Long> balances(long... nets) {
        Map<String, Long> m = new LinkedHashMap<>();
        for (int i = 0; i < nets.length; i++) {
            m.put("P" + i, nets[i]);
        }
        return m;
    }

    /** Applying the plan must bring every balance to exactly zero, with sane transfers. */
    private static void assertSettles(Map<String, Long> balances, SettlementPlan plan) {
        Map<String, Long> left = new HashMap<>(balances);
        for (Settlement s : plan.settlements()) {
            assertTrue(s.amountPaise() > 0, "non-positive transfer " + s);
            assertFalse(s.from().equals(s.to()), "self transfer " + s);
            assertTrue(balances.get(s.from()) < 0, "payer must be a debtor: " + s);
            assertTrue(balances.get(s.to()) > 0, "receiver must be a creditor: " + s);
            left.merge(s.from(), s.amountPaise(), Long::sum);
            left.merge(s.to(), -s.amountPaise(), Long::sum);
        }
        left.values().forEach(v -> assertEquals(0L, v, "unsettled balance left: " + left));
    }

    /** Reference answer: exhaustive search for the minimum number of transfers. Fine for n <= 8. */
    private static int bruteForceMinimum(long[] nets) {
        long[] debt = Arrays.stream(nets).filter(v -> v != 0).toArray();
        return dfs(debt, 0);
    }

    private static int dfs(long[] debt, int start) {
        while (start < debt.length && debt[start] == 0) {
            start++;
        }
        if (start == debt.length) {
            return 0;
        }
        int best = Integer.MAX_VALUE;
        for (int i = start + 1; i < debt.length; i++) {
            if (debt[i] * debt[start] < 0) {
                debt[i] += debt[start];
                best = Math.min(best, 1 + dfs(debt, start + 1));
                debt[i] -= debt[start];
            }
        }
        return best;
    }

    @Test
    void nothingToSettle() {
        assertTrue(DebtSimplifier.simplify(Map.of()).settlements().isEmpty());
        assertTrue(DebtSimplifier.simplify(balances(0, 0, 0)).settlements().isEmpty());
    }

    @Test
    void oneDebtorOneCreditor() {
        SettlementPlan plan = DebtSimplifier.simplify(balances(-500, 500));
        assertEquals(List.of(new Settlement("P0", "P1", 500)), plan.settlements());
        assertTrue(plan.optimal());
    }

    @Test
    void chainCollapsesToOneTransfer() {
        // A owes B 100 and B owes C 100 -> A pays C directly.
        Map<String, Long> b = balances(-100, 0, 100);
        SettlementPlan plan = DebtSimplifier.simplify(b);
        assertEquals(List.of(new Settlement("P0", "P2", 100)), plan.settlements());
    }

    @Test
    void beatsGreedyWhenZeroSumGroupsExist() {
        // Two independent groups: {+10, -6, -4} and {+9, -9}. Greedy mixes them and needs 4 transfers.
        Map<String, Long> b = balances(1000, 900, -900, -600, -400);
        SettlementPlan plan = DebtSimplifier.simplify(b);
        assertSettles(b, plan);
        assertEquals(3, plan.settlements().size());
        assertEquals(4, DebtSimplifier.greedy(b).size());
    }

    @RepeatedTest(5)
    void matchesBruteForceMinimumOnRandomGroups() {
        Random rnd = new Random();
        for (int trial = 0; trial < 300; trial++) {
            int n = 2 + rnd.nextInt(7);
            long[] nets = new long[n];
            long sum = 0;
            for (int i = 0; i < n - 1; i++) {
                // Small values make zero-sum subgroups (the hard case) common.
                nets[i] = (rnd.nextInt(11) - 5) * 100L;
                sum += nets[i];
            }
            nets[n - 1] = -sum;
            Map<String, Long> b = balances(nets);
            SettlementPlan plan = DebtSimplifier.simplify(b);
            assertSettles(b, plan);
            assertEquals(bruteForceMinimum(nets), plan.settlements().size(), "nets=" + Arrays.toString(nets));
            assertTrue(plan.optimal());
        }
    }

    @Test
    @Timeout(5)
    void exactAlgorithmAtItsLimitIsFast() {
        long[] nets = new long[DebtSimplifier.EXACT_LIMIT];
        Random rnd = new Random(42);
        long sum = 0;
        for (int i = 0; i < nets.length - 1; i++) {
            nets[i] = (rnd.nextInt(2001) - 1000) * 100L + (i % 2 == 0 ? 1 : -1);
            sum += nets[i];
        }
        nets[nets.length - 1] = -sum;
        Map<String, Long> b = balances(nets);
        SettlementPlan plan = DebtSimplifier.simplify(b);
        assertTrue(plan.optimal());
        assertSettles(b, plan);
    }

    @Test
    @Timeout(5)
    void largeGroupsFallBackToGreedyWithinNMinusOne() {
        Random rnd = new Random(7);
        int n = 5_000;
        long[] nets = new long[n];
        long sum = 0;
        for (int i = 0; i < n - 1; i++) {
            nets[i] = rnd.nextInt(2_000_001) - 1_000_000;
            sum += nets[i];
        }
        nets[n - 1] = -sum;
        Map<String, Long> b = balances(nets);
        SettlementPlan plan = DebtSimplifier.simplify(b);
        assertFalse(plan.optimal());
        assertSettles(b, plan);
        assertTrue(plan.settlements().size() <= n - 1);
    }

    @Test
    void rejectsBalancesThatDoNotSumToZero() {
        assertThrows(IllegalArgumentException.class, () -> DebtSimplifier.simplify(balances(100, -99)));
    }

    @Test
    void outputIsDeterministic() {
        Map<String, Long> b = balances(300, 300, -200, -200, -200);
        assertEquals(DebtSimplifier.simplify(b), DebtSimplifier.simplify(new LinkedHashMap<>(b)));
    }
}
