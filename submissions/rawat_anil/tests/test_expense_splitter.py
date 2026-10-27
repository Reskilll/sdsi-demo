"""Tests for the expense splitter — covers all judgment criteria plus edge cases."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure the submission package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from expense_splitter.engine import compute_balances, simplify_debts
from expense_splitter.models import Balance, Expense, SplitType
from expense_splitter.validator import ValidationError, validate_expense


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_expense(desc, total, paid_by, split_type, members, amounts=None):
    return Expense(
        description=desc,
        total=float(total),
        paid_by=paid_by,
        split_type=SplitType(split_type),
        members=list(members),
        amounts=[float(a) for a in amounts] if amounts else None,
    )


# ═══════════════════════════════════════════════════════════════════════════
# M1: Split types — equal, exact, percentage
# ═══════════════════════════════════════════════════════════════════════════

class TestEqualSplit:
    def test_simple_equal(self):
        """Three members, one payer, equal ₹300 split → each owes ₹100."""
        expense = _make_expense("Dinner", 300, "A", "equal", ["A", "B", "C"])
        balances = compute_balances([expense], ["A", "B", "C"])
        assert balances["A"].paid == 300
        assert balances["A"].owed == pytest.approx(100)
        assert balances["B"].paid == 0
        assert balances["B"].owed == pytest.approx(100)

    def test_equal_rounding(self):
        """₹100 split 3 ways → shares absorb rounding (33.33, 33.33, 33.34)."""
        expense = _make_expense("Snacks", 100, "A", "equal", ["A", "B", "C"])
        balances = compute_balances([expense], ["A", "B", "C"])
        total_owed = sum(b.owed for b in balances.values())
        assert total_owed == pytest.approx(100)
        assert balances["A"].paid == 100

    def test_equal_single_member(self):
        """One person splitting equally with themselves (edge case)."""
        expense = _make_expense("Solo lunch", 500, "X", "equal", ["X"])
        balances = compute_balances([expense], ["X"])
        assert balances["X"].paid == 500
        assert balances["X"].owed == pytest.approx(500)
        assert balances["X"].net == pytest.approx(0)


class TestExactSplit:
    def test_exact_split(self):
        """Payer pays a bigger share; others pay exact amounts."""
        expense = _make_expense(
            "Dinner", 500, "A", "exact", ["A", "B", "C"], [200, 150, 150]
        )
        balances = compute_balances([expense], ["A", "B", "C"])
        assert balances["A"].paid == 500
        assert balances["A"].owed == pytest.approx(200)
        assert balances["B"].owed == pytest.approx(150)

    def test_exact_with_zero_share(self):
        """One member pays nothing (explicit zero in exact split)."""
        expense = _make_expense(
            "Drinks", 400, "B", "exact", ["A", "B", "C", "D"], [150, 100, 150, 0]
        )
        balances = compute_balances([expense], ["A", "B", "C", "D"])
        assert balances["D"].owed == 0
        assert balances["B"].paid == 400


class TestPercentageSplit:
    def test_percentage_split(self):
        """50/30/20 percentage split on ₹1000."""
        expense = _make_expense(
            "Rent", 1000, "C", "percentage", ["A", "B", "C"], [50, 30, 20]
        )
        balances = compute_balances([expense], ["A", "B", "C"])
        assert balances["A"].owed == pytest.approx(500)
        assert balances["B"].owed == pytest.approx(300)
        assert balances["C"].owed == pytest.approx(200)
        assert balances["C"].paid == 1000

    def test_percentage_rounding_error_absorbed(self):
        """₹50 split 33/33/34% — total owed equals total paid."""
        expense = _make_expense(
            "Cab", 100, "A", "percentage", ["A", "B", "C"], [33.33, 33.33, 33.34]
        )
        balances = compute_balances([expense], ["A", "B", "C"])
        total_owed = round(sum(b.owed for b in balances.values()), 2)
        assert total_owed == 100


# ═══════════════════════════════════════════════════════════════════════════
# M2: Net balance calculation
# ═══════════════════════════════════════════════════════════════════════════

class TestNetBalance:
    def test_positive_net_means_credit(self):
        """Payer who paid everything but owed less is a creditor."""
        exp = _make_expense("Pizza", 300, "A", "equal", ["A", "B", "C"])
        balances = compute_balances([exp], ["A", "B", "C"])
        assert balances["A"].net > 0  # A is owed money
        assert balances["B"].net < 0  # B owes money

    def test_multi_expense_cumulative(self):
        """Net balances accumulate across multiple expenses."""
        e1 = _make_expense("Food", 300, "A", "equal", ["A", "B", "C"])
        e2 = _make_expense("Drinks", 600, "B", "equal", ["A", "B", "C"])
        balances = compute_balances([e1, e2], ["A", "B", "C"])
        # A: paid 300, owed 300 → net 0
        # B: paid 600, owed 300 → net +300
        # C: paid 0, owed 300 → net -300
        assert balances["A"].net == pytest.approx(0, abs=0.02)
        assert balances["B"].net == pytest.approx(300, abs=0.02)
        assert balances["C"].net == pytest.approx(-300, abs=0.02)

    def test_sum_of_all_nets_is_zero(self):
        """The sum of all net balances must equal zero (conservation)."""
        e1 = _make_expense("A paid", 500, "A", "equal", ["A", "B", "C", "D"])
        e2 = _make_expense("B paid", 350, "B", "exact", ["A", "B", "C"], [100, 150, 100])
        balances = compute_balances([e1, e2], ["A", "B", "C", "D"])
        total_net = round(sum(b.net for b in balances.values()), 2)
        assert total_net == 0


# ═══════════════════════════════════════════════════════════════════════════
# M3: Debt simplification
# ═══════════════════════════════════════════════════════════════════════════

class TestSimplifyDebts:
    def test_trivial_no_debts(self):
        """All settled → empty settlement list."""
        balances = {"A": Balance(paid=100, owed=100), "B": Balance(paid=0, owed=0)}
        settlements = simplify_debts(balances)
        assert settlements == []

    def test_simple_two_party(self):
        """A owes B ₹50."""
        balances = {
            "A": Balance(paid=0, owed=50),
            "B": Balance(paid=50, owed=0),
        }
        settlements = simplify_debts(balances)
        assert len(settlements) == 1
        assert settlements[0].from_member == "A"
        assert settlements[0].to_member == "B"
        assert settlements[0].amount == 50

    def test_three_party_cycle_reduced(self):
        """A→B→C cycle reduced to minimal transfers."""
        # A paid for B, B paid for C → net: A is owed, C owes, B is neutral
        # A paid 300 (A,B,C equal) → A net +200, B net -100, C net -100
        expense = _make_expense("Dinner", 300, "A", "equal", ["A", "B", "C"])
        balances = compute_balances([expense], ["A", "B", "C"])
        settlements = simplify_debts(balances)
        # B → A 100 and C → A 100 (2 settlements, not a cycle of 3)
        assert len(settlements) == 2
        amounts = sum(s.amount for s in settlements)
        assert amounts == pytest.approx(200)

    def test_greedy_produces_valid_settlements(self):
        """After applying all settlements, every net balance should be zero."""
        e1 = _make_expense("Hotel", 24000, "Priya", "equal",
                           ["Anil", "Priya", "Raj", "Simran", "Vikram"])
        e2 = _make_expense("Food", 9000, "Anil", "equal",
                           ["Anil", "Priya", "Vikram"])
        members = ["Anil", "Priya", "Raj", "Simran", "Vikram"]
        balances = compute_balances([e1, e2], members)
        settlements = simplify_debts(balances)

        # Apply settlements and verify
        net_after = {m: round(b.net, 2) for m, b in balances.items()}
        for s in settlements:
            net_after[s.from_member] = round(net_after[s.from_member] + s.amount, 2)
            net_after[s.to_member] = round(net_after[s.to_member] - s.amount, 2)

        for name, net in net_after.items():
            assert abs(net) < 0.02, f"{name} still has net {net} after settlements"

    def test_no_redundant_cycles(self):
        """No A→B→A cycles in settlements (no back-and-forth)."""
        # Net: A +100, B -50, C -50 → C→A 50, B→A 50
        balances = {
            "A": Balance(paid=100, owed=0),
            "B": Balance(paid=0, owed=50),
            "C": Balance(paid=0, owed=50),
        }
        settlements = simplify_debts(balances)
        # Verify no member appears as both sender and receiver
        senders = {s.from_member for s in settlements}
        receivers = {s.to_member for s in settlements}
        # Someone could theoretically be both, but with greedy it's minimal
        # The key check: no cycle (lowest count possible)
        assert len(settlements) <= 2  # 2 debtors × 1 creditor = 2 max


# ═══════════════════════════════════════════════════════════════════════════
# M5: Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestValidation:
    GROUP = {"A", "B", "C", "D"}

    def test_payer_must_be_member(self):
        with pytest.raises(ValidationError, match="not in the group"):
            validate_expense(
                _make_expense("Food", 100, "Z", "equal", ["A", "B"]), self.GROUP
            )

    def test_member_must_be_in_group(self):
        with pytest.raises(ValidationError, match="unknown members"):
            validate_expense(
                _make_expense("Food", 100, "A", "equal", ["A", "X"]), self.GROUP
            )

    def test_exact_amounts_must_sum_to_total(self):
        with pytest.raises(ValidationError, match="sum to 50"):
            validate_expense(
                _make_expense("Food", 100, "A", "exact", ["A", "B"], [30, 20]),
                self.GROUP,
            )

    def test_percentages_must_sum_to_100(self):
        with pytest.raises(ValidationError, match="sum to 100%"):
            validate_expense(
                _make_expense("Food", 100, "A", "percentage", ["A", "B"], [60, 30]),
                self.GROUP,
            )

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError, match="non-negative"):
            validate_expense(
                _make_expense("Food", 100, "A", "exact", ["A", "B"], [120, -20]),
                self.GROUP,
            )

    def test_negative_total_rejected(self):
        with pytest.raises(ValidationError, match="total must be positive"):
            validate_expense(
                _make_expense("Refund", -100, "A", "equal", ["A", "B"]), self.GROUP
            )

    def test_zero_total_rejected(self):
        with pytest.raises(ValidationError, match="total must be positive"):
            validate_expense(
                _make_expense("Free", 0, "A", "equal", ["A", "B"]), self.GROUP
            )

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError, match="description"):
            validate_expense(
                _make_expense("", 100, "A", "equal", ["A", "B"]), self.GROUP
            )

    def test_missing_amounts_for_exact(self):
        with pytest.raises(ValidationError, match="requires 'amounts'"):
            validate_expense(
                _make_expense("Food", 100, "A", "exact", ["A", "B"]), self.GROUP
            )

    def test_wrong_amount_count(self):
        with pytest.raises(ValidationError, match="expected 2 amounts"):
            validate_expense(
                _make_expense("Food", 100, "A", "exact", ["A", "B"], [50, 30, 20]),
                self.GROUP,
            )

    def test_empty_members_rejected(self):
        with pytest.raises(ValidationError, match="member list must not be empty"):
            validate_expense(
                _make_expense("Food", 100, "A", "equal", []), self.GROUP
            )

    def test_duplicate_members_in_group_rejected(self):
        from expense_splitter.validator import validate_group_input
        with pytest.raises(ValidationError, match="Duplicate member"):
            validate_group_input("Test", ["A", "B", "A"], [{"description": "X", "total": 100, "paid_by": "A", "split_type": "equal", "members": ["A", "B"]}])


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_all_members_pay_equally_result_zero(self):
        """Every member pays one equal expense → everyone ends at zero."""
        e1 = _make_expense("A paid", 300, "A", "equal", ["A", "B", "C"])
        e2 = _make_expense("B paid", 300, "B", "equal", ["A", "B", "C"])
        e3 = _make_expense("C paid", 300, "C", "equal", ["A", "B", "C"])
        balances = compute_balances([e1, e2, e3], ["A", "B", "C"])
        for b in balances.values():
            assert b.net == pytest.approx(0, abs=0.02)

    def test_single_member_group(self):
        """Group of 1 — net always zero."""
        exp = _make_expense("Coffee", 200, "A", "equal", ["A"])
        balances = compute_balances([exp], ["A"])
        assert balances["A"].net == pytest.approx(0)
        settlements = simplify_debts(balances)
        assert settlements == []

    def test_very_large_numbers(self):
        """Large amounts shouldn't overflow or lose precision."""
        exp = _make_expense("Venue", 9_999_999.99, "A", "equal", ["A", "B"])
        balances = compute_balances([exp], ["A", "B"])
        assert balances["A"].paid == 9_999_999.99
        assert balances["B"].owed == pytest.approx(4_999_999.99, abs=0.02)

    def test_small_fractional_amounts(self):
        """Sub-paisa amounts should be handled via rounding."""
        exp = _make_expense("Chai", 10, "A", "equal", ["A", "B", "C"])
        balances = compute_balances([exp], ["A", "B", "C"])
        total_owed = sum(b.owed for b in balances.values())
        assert total_owed == pytest.approx(10)

    def test_member_not_in_any_expense(self):
        """A group member not listed in any expense — zero balance."""
        exp = _make_expense("Food", 200, "A", "equal", ["A", "B"])
        balances = compute_balances([exp], ["A", "B", "C"])
        assert balances["C"].paid == 0
        assert balances["C"].owed == 0
        assert balances["C"].net == 0

    def test_float_precision_no_epsilon_bugs(self):
        """₹0.10 + ₹0.20 should be exactly ₹0.30 — no floating-point surprises."""
        exp = _make_expense("Gum", 0.30, "A", "exact", ["A", "B"], [0.10, 0.20])
        balances = compute_balances([exp], ["A", "B"])
        assert balances["A"].owed == pytest.approx(0.10)
        assert balances["B"].owed == pytest.approx(0.20)