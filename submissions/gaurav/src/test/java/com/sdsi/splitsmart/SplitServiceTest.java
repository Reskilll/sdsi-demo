package com.sdsi.splitsmart;

import com.sdsi.splitsmart.dto.*;
import com.sdsi.splitsmart.model.*;
import com.sdsi.splitsmart.service.SplitService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class SplitServiceTest {

    private final SplitService service = new SplitService();

    // ─── M1: EQUAL split ──────────────────────────────────────────────────

    @Test
    void equalSplit() {
        var req = new ExpenseRequest("Alice", 300, SplitType.EQUAL,
                List.of("Alice", "Bob", "Charlie"), null);
        GroupSnapshot snap = service.addExpense(req);

        assertBalance(snap, "Alice", -200);  // paid 300, owes 100 → net -200
        assertBalance(snap, "Bob", 100);
        assertBalance(snap, "Charlie", 100);
    }

    // ─── M1: EXACT split ──────────────────────────────────────────────────

    @Test
    void exactSplit() {
        var req = new ExpenseRequest("Bob", 500, SplitType.EXACT,
                List.of("Alice", "Bob", "Charlie"),
                Map.of("Alice", 200.0, "Bob", 100.0, "Charlie", 200.0));
        GroupSnapshot snap = service.addExpense(req);

        assertBalance(snap, "Alice", 200);    // owes 200
        assertBalance(snap, "Bob", -400);     // paid 500, owes 100 → net -400
        assertBalance(snap, "Charlie", 200);  // owes 200
    }

    // ─── M1: PERCENTAGE split ─────────────────────────────────────────────

    @Test
    void percentageSplit() {
        var req = new ExpenseRequest("Charlie", 200, SplitType.PERCENTAGE,
                List.of("Alice", "Charlie"),
                Map.of("Alice", 30.0, "Charlie", 70.0));
        GroupSnapshot snap = service.addExpense(req);

        assertBalance(snap, "Alice", 60);      // 30% of 200
        assertBalance(snap, "Charlie", -60);    // paid 200, owes 70% → net 200 - 140 = 60 "owed" → -60
    }

    // ─── M2: Net balances across multiple expenses ────────────────────────

    @Test
    void netBalancesAcrossMultipleExpenses() {
        service.addExpense(new ExpenseRequest("Alice", 300, SplitType.EQUAL,
                List.of("Alice", "Bob", "Charlie"), null));
        service.addExpense(new ExpenseRequest("Bob", 600, SplitType.EQUAL,
                List.of("Alice", "Bob", "Charlie"), null));

        GroupSnapshot snap = service.getSnapshot();
        // Alice: paid 300 owes 100+200 → net 300-300=0
        assertBalance(snap, "Alice", 0);
        // Bob: paid 600 owes 100+200 → net 600-300=300 credit → -300
        assertBalance(snap, "Bob", -300);
        // Charlie: owes 100+200 = 300
        assertBalance(snap, "Charlie", 300);
    }

    // ─── M3: Simplified settlements ───────────────────────────────────────

    @Test
    void simplifiedSettlements() {
        service.addExpense(new ExpenseRequest("Alice", 300, SplitType.EQUAL,
                List.of("Alice", "Bob", "Charlie"), null));
        service.addExpense(new ExpenseRequest("Bob", 600, SplitType.EQUAL,
                List.of("Alice", "Bob", "Charlie"), null));

        GroupSnapshot snap = service.getSnapshot();
        List<Settlement> settlements = snap.settlements();

        // Charlie owes 300 total. Alice=0, Bob is owed 300.
        // → Charlie pays Bob 300
        assertEquals(1, settlements.size());
        assertEquals("Charlie", settlements.get(0).from());
        assertEquals("Bob", settlements.get(0).to());
        assertEquals(300.0, settlements.get(0).amount(), 0.01);
    }

    // ─── M5: Validation — payer not in members ────────────────────────────

    @Test
    void rejectPayerNotInMembers() {
        var req = new ExpenseRequest("Zoe", 100, SplitType.EQUAL,
                List.of("Alice", "Bob"), null);
        assertThrows(IllegalArgumentException.class, () -> service.addExpense(req));
    }

    // ─── M5: Validation — percentages don't sum to 100 ────────────────────

    @Test
    void rejectBadPercentages() {
        var req = new ExpenseRequest("Alice", 100, SplitType.PERCENTAGE,
                List.of("Alice", "Bob"),
                Map.of("Alice", 40.0, "Bob", 50.0)); // sums to 90
        assertThrows(IllegalArgumentException.class, () -> service.addExpense(req));
    }

    // ─── M5: Validation — exact shares don't sum to total ─────────────────

    @Test
    void rejectBadExact() {
        var req = new ExpenseRequest("Alice", 100, SplitType.EXACT,
                List.of("Alice", "Bob"),
                Map.of("Alice", 30.0, "Bob", 40.0)); // sums to 70 ≠ 100
        assertThrows(IllegalArgumentException.class, () -> service.addExpense(req));
    }

    // ─── M4: Batch processing ─────────────────────────────────────────────

    @Test
    void batchProcessing() {
        GroupSnapshot snap = service.addBatch(List.of(
                new ExpenseRequest("Alice", 100, SplitType.EQUAL,
                        List.of("Alice", "Bob"), null),
                new ExpenseRequest("Bob", 100, SplitType.EQUAL,
                        List.of("Alice", "Bob"), null)
        ));

        assertBalance(snap, "Alice", 0);
        assertBalance(snap, "Bob", 0);
    }

    private void assertBalance(GroupSnapshot snap, String member, double expected) {
        for (var b : snap.balances()) {
            if (b.member().equals(member)) {
                assertEquals(expected, b.netOwed(), 0.01,
                        "Balance mismatch for " + member);
                return;
            }
        }
        fail("Member " + member + " not found in balances");
    }
}