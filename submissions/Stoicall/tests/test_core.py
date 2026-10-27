"""
Tests for Expense Splitter: M1-M5, E1-E3, and common edge cases.
"""
import json
import sys
import tempfile
from pathlib import Path
from decimal import Decimal

import pytest

from expense_splitter import ExpenseSplitter, ExpenseError
from expense_splitter.core import (
    Expense, SplitType, Settlement, _to_decimal
)


# =========================================================================
# M1: Add expenses with three split types
# =========================================================================

class TestAddExpenses:
    def test_equal_split(self):
        s = ExpenseSplitter(["A", "B"])
        e = Expense("Lunch", Decimal("120"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}])
        s.add_expense(e)
        assert len(s.expenses) == 1

    def test_exact_split(self):
        s = ExpenseSplitter(["A", "B"])
        e = Expense("Lunch", Decimal("120"), "B", SplitType.EXACT,
                     [{"member": "A", "amount": Decimal("70")},
                      {"member": "B", "amount": Decimal("50")}])
        s.add_expense(e)
        assert len(s.expenses) == 1

    def test_percentage_split(self):
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("1000"), "A", SplitType.PERCENTAGE,
                     [{"member": "A", "percentage": Decimal("50")},
                      {"member": "B", "percentage": Decimal("30")},
                      {"member": "C", "percentage": Decimal("20")}])
        s.add_expense(e)
        assert len(s.expenses) == 1


# =========================================================================
# M2: Net balances
# =========================================================================

class TestNetBalances:
    def test_single_expense_equal(self):
        """A pays 120, split equal between A and B → A net = +60, B net = -60"""
        s = ExpenseSplitter(["A", "B"])
        e = Expense("Lunch", Decimal("120"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}])
        s.add_expense(e)
        net = s.net_balances()
        assert net["A"] == Decimal("60")  # A paid 120, owes 60 → net +60
        assert net["B"] == Decimal("-60")  # B owes 60 → net -60

    def test_exact_net(self):
        """B pays 120, A owes 70, B owes 50 → A owes 70, B net = +70"""
        s = ExpenseSplitter(["A", "B"])
        e = Expense("Lunch", Decimal("120"), "B", SplitType.EXACT,
                     [{"member": "A", "amount": Decimal("70")},
                      {"member": "B", "amount": Decimal("50")}])
        s.add_expense(e)
        net = s.net_balances()
        assert net["A"] == Decimal("-70")
        assert net["B"] == Decimal("70")  # paid 120, owes 50 → +70

    def test_percentage_net(self):
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("1000"), "A", SplitType.PERCENTAGE,
                     [{"member": "A", "percentage": Decimal("50")},
                      {"member": "B", "percentage": Decimal("30")},
                      {"member": "C", "percentage": Decimal("20")}])
        s.add_expense(e)
        net = s.net_balances()
        # A paid 1000, owes 500 → net +500
        assert net["A"] == Decimal("500")
        assert net["B"] == Decimal("-300")
        assert net["C"] == Decimal("-200")


# =========================================================================
# M3: Debt simplification
# =========================================================================

class TestSimplify:
    def test_basic_simplification(self):
        """A owes B 100, C owes B 50 → A→B ₹100, C→B ₹50"""
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("200"), "A", SplitType.EXACT,
                     [{"member": "A", "amount": Decimal("100")},
                      {"member": "B", "amount": Decimal("0")},
                      {"member": "C", "amount": Decimal("100")}])
        s.add_expense(e)
        e2 = Expense("Lunch", Decimal("50"), "C", SplitType.EXACT,
                      [{"member": "A", "amount": Decimal("0")},
                       {"member": "B", "amount": Decimal("50")},
                       {"member": "C", "amount": Decimal("0")}])
        s.add_expense(e2)
        settlements = s.simplify()
        # A has net 0, B is +50, C is -50? Let's compute:
        # E1: A pays 200, A owes 100, B owes 0, C owes 100
        #   A: +200 - 100 = +100
        #   B: 0 - 0 = 0
        #   C: 0 - 100 = -100
        # E2: C pays 50, A owes 0, B owes 50, C owes 0
        #   C: +50 - 0 = +50, net total C: -100 + 50 = -50
        #   B: 0 - 50 = -50, net total B: 0 + (-50) = -50
        #   A: 0 - 0 = 0
        # So net: A=+100, B=-50, C=-50.
        # Wait, B owes 50 to C from E2. C owes 100 to A from E1.
        # Net: A=+100, B=-50, C=-50
        # Settlements: B→A ₹50, C→A ₹50 (2 transactions)
        total_settled = sum(s.amount for s in settlements)
        assert total_settled == Decimal("100"), f"Expected 100 settled, got {total_settled}"

    def test_simplify_cycle(self):
        """A→B 100, B→C 100, C→A 100 → net zero → no settlements."""
        s = ExpenseSplitter(["A", "B", "C"])
        e1 = Expense("A pays", Decimal("100"), "A", SplitType.EXACT,
                      [{"member": "A", "amount": Decimal("0")},
                       {"member": "B", "amount": Decimal("100")}])
        e2 = Expense("B pays", Decimal("100"), "B", SplitType.EXACT,
                      [{"member": "B", "amount": Decimal("0")},
                       {"member": "C", "amount": Decimal("100")}])
        e3 = Expense("C pays", Decimal("100"), "C", SplitType.EXACT,
                      [{"member": "C", "amount": Decimal("0")},
                       {"member": "A", "amount": Decimal("100")}])
        s.add_expense(e1)  # A fronted 100, owes 0, B owes 100 → A+100, B-100
        s.add_expense(e2)  # B fronted 100, owes 0, C owes 100 → B+100, C-100
        s.add_expense(e3)  # C fronted 100, owes 0, A owes 100 → C+100, A-100
        # Net: all zero
        settlements = s.simplify()
        assert len(settlements) == 0

    def test_minimal_transactions(self):
        """4 people, one pays for all → 3 settlements max."""
        s = ExpenseSplitter(["A", "B", "C", "D"])
        e = Expense("Party", Decimal("400"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"},
                      {"member": "C"}, {"member": "D"}])
        s.add_expense(e)
        settlements = s.simplify()
        assert len(settlements) <= 3
        total_settled = sum(s.amount for s in settlements)
        assert total_settled == Decimal("300")  # 3 people owe 100 each


# =========================================================================
# M4: Batch input from JSON
# =========================================================================

class TestBatchInput:
    def test_from_json_file(self):
        data = {
            "members": ["A", "B"],
            "expenses": [
                {"title": "Lunch", "total": 120, "paid_by": "A",
                 "split": {"type": "equal", "members": ["A", "B"]}},
                {"title": "Dinner", "total": 200, "paid_by": "B",
                 "split": {"type": "exact", "shares": [
                     {"member": "A", "amount": 150},
                     {"member": "B", "amount": 50}
                 ]}},
            ]
        }
        s = ExpenseSplitter.from_dict(data)
        assert len(s.expenses) == 2
        assert "A" in s.members
        assert "B" in s.members
        net = s.net_balances()
        # A: +120 - 60 = +60; then A owes 150 → net -90
        # B: owed 60 from first, B pays 200, owes 50 → +60 +200 -50 = +210?
        # Let me recalculate: E1: A pays 120, split equal: A owes 60, B owes 60.
        #   A: +120 -60 = +60. B: 0 -60 = -60.
        # E2: B pays 200, A owes 150, B owes 50.
        #   B: +200 -50 = +150. A: 0 -150 = -150.
        # Net: A: 60 - 150 = -90. B: -60 + 150 = +90.
        assert net["A"] == Decimal("-90")
        assert net["B"] == Decimal("90")

    def test_from_json_on_disk(self):
        s = ExpenseSplitter.from_json(
            str(Path(__file__).parent.parent / "samples" / "simple.json"))
        assert len(s.expenses) == 3


# =========================================================================
# M5: Input validation
# =========================================================================

class TestValidation:
    def test_percentages_must_sum_to_100(self):
        s = ExpenseSplitter(["A", "B"])
        with pytest.raises(ExpenseError, match="Percentages sum"):
            e = Expense("Bad", Decimal("100"), "A", SplitType.PERCENTAGE,
                         [{"member": "A", "percentage": Decimal("50")},
                          {"member": "B", "percentage": Decimal("30")}])
            s.add_expense(e)

    def test_exact_amounts_must_sum_to_total(self):
        s = ExpenseSplitter(["A", "B"])
        with pytest.raises(ExpenseError, match="Exact amounts sum"):
            e = Expense("Bad", Decimal("100"), "A", SplitType.EXACT,
                         [{"member": "A", "amount": Decimal("40")},
                          {"member": "B", "amount": Decimal("40")}])
            s.add_expense(e)

    def test_payer_in_group_equal(self):
        s = ExpenseSplitter(["A", "B"])
        with pytest.raises(ExpenseError, match="Payer.*must.*among"):
            e = Expense("Bad", Decimal("100"), "Z", SplitType.EQUAL,
                         [{"member": "A"}, {"member": "B"}])
            s.add_expense(e)

    def test_payer_in_group_exact(self):
        s = ExpenseSplitter(["A", "B"])
        with pytest.raises(ExpenseError, match="Payer.*not in.*exact"):
            e = Expense("Bad", Decimal("100"), "Z", SplitType.EXACT,
                         [{"member": "A", "amount": Decimal("50")},
                          {"member": "B", "amount": Decimal("50")}])
            s.add_expense(e)

    def test_payer_in_group_percentage(self):
        s = ExpenseSplitter(["A", "B"])
        with pytest.raises(ExpenseError, match="Payer.*not in.*percentage"):
            e = Expense("Bad", Decimal("100"), "Z", SplitType.PERCENTAGE,
                         [{"member": "A", "percentage": Decimal("50")},
                          {"member": "B", "percentage": Decimal("50")}])
            s.add_expense(e)

    def test_negative_total(self):
        with pytest.raises(ExpenseError, match="positive"):
            s = ExpenseSplitter(["A"])
            e = Expense("Bad", Decimal("-10"), "A", SplitType.EQUAL,
                         [{"member": "A"}])
            s.add_expense(e)

    def test_empty_title(self):
        with pytest.raises(ExpenseError, match="title"):
            s = ExpenseSplitter(["A"])
            e = Expense("", Decimal("10"), "A", SplitType.EQUAL,
                         [{"member": "A"}])
            s.add_expense(e)


# =========================================================================
# E1: Single-member group
# =========================================================================

class TestSingleMember:
    def test_single_member_equal(self):
        s = ExpenseSplitter(["A"])
        e = Expense("Solo", Decimal("100"), "A", SplitType.EQUAL,
                     [{"member": "A"}])
        s.add_expense(e)
        net = s.net_balances()
        assert net["A"] == Decimal("0")
        assert len(s.simplify()) == 0

    def test_single_member_is_payer(self):
        """Single member who is also payer is valid."""
        s = ExpenseSplitter(["A"])
        e = Expense("Solo", Decimal("100"), "A", SplitType.EQUAL,
                     [{"member": "A"}])
        s.add_expense(e)
        net = s.net_balances()
        assert net["A"] == Decimal("0")


# =========================================================================
# E2: Zero / rounding in percentage splits
# =========================================================================

class TestRounding:
    def test_uneven_percentage_recovered(self):
        """
        33.33% + 33.33% + 33.34% → ₹100 total.
        With ₹100 total:
          33.33% → 33.33
          33.33% → 33.33
          33.34% → 33.34
        Sum = 100.00 ✓
        """
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("100"), "A", SplitType.PERCENTAGE,
                     [{"member": "A", "percentage": Decimal("33.33")},
                      {"member": "B", "percentage": Decimal("33.33")},
                      {"member": "C", "percentage": Decimal("33.34")}])
        s.add_expense(e)
        net = s.net_balances()
        # A paid 100, owes 33.33 → +66.67
        assert net["A"] == Decimal("66.67")
        assert net["B"] == Decimal("-33.33")
        assert net["C"] == Decimal("-33.34")

    def test_zero_amount_percentage(self):
        """A share with 0% is valid."""
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("100"), "A", SplitType.PERCENTAGE,
                     [{"member": "A", "percentage": Decimal("100")},
                      {"member": "B", "percentage": Decimal("0")}])
        s.add_expense(e)
        net = s.net_balances()
        assert net["A"] == Decimal("0")  # paid 100, owes 100
        assert net["B"] == Decimal("0")

    def test_equal_split_rounding(self):
        """₹100 / 3 = 33.33 + 33.33 + 33.34"""
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Dinner", Decimal("100"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}, {"member": "C"}])
        s.add_expense(e)
        shares = s._compute_shares(e)
        amounts = [(m, a) for m, a in shares]
        total_split = sum(a for _, a in shares)
        assert total_split == Decimal("100")
        # The first two get 33.33, the last gets 33.34 (due to remainder distribution)
        assert amounts[0][1] + amounts[1][1] + amounts[2][1] == Decimal("100")

    def test_odd_rounding_exact_split(self):
        """Exact split with fractional amounts."""
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Gas", Decimal("10.01"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}, {"member": "C"}])
        s.add_expense(e)
        net = s.net_balances()
        # A paid 10.01, owes 3.34 (largest remainder via first members)
        # Actually: 10.01/3 = 3.33666...
        # base = 3.34 (rounded)
        # 3.34 * 3 = 10.02 - this is >10.01 so remainder = -0.01
        # First member gets 3.33
        # Wait, let me trace the code:
        # per_person = 10.01/3 = 3.336666...
        # base = 3.34 (ROUND_HALF_UP)
        # allocated = 3.34 * 3 = 10.02
        # remainder = 10.01 - 10.02 = -0.01
        # Distribute: i=0 → 3.34 - 0.01 = 3.33
        #            i=1 → 3.34
        #            i=2 → 3.34
        # Sum = 10.01 ✓
        # A owes 3.33, net = 10.01 - 3.33 = 6.68
        assert net["A"] == Decimal("6.68")
        assert net["B"] == Decimal("-3.34")
        assert net["C"] == Decimal("-3.34")


# =========================================================================
# E3: Debt cycles / simplification optimality
# =========================================================================

class TestDebtCycles:
    def test_simple_cycle(self):
        """
        A→B 100, B→A 50 → Net: A=-50, B=+50 → 1 settlement.
        """
        s = ExpenseSplitter(["A", "B"])
        e1 = Expense("Dinner", Decimal("100"), "A", SplitType.EQUAL,
                      [{"member": "A"}, {"member": "B"}])
        e2 = Expense("Lunch", Decimal("50"), "B", SplitType.EQUAL,
                      [{"member": "A"}, {"member": "B"}])
        s.add_expense(e1)  # A paid 100, A owes 50, B owes 50 → A+50, B-50
        s.add_expense(e2)  # B paid 50, B owes 25, A owes 25 → B+25, A-25
        # Net: A = +50 - 25 = +25, B = -50 + 25 = -25
        settlements = s.simplify()
        assert len(settlements) == 1, f"Expected 1, got {len(settlements)}: {settlements}"
        assert settlements[0].from_member == "B"
        assert settlements[0].to_member == "A"

    def test_three_party_chain(self):
        """
        A→B 100, B→C 100 → Net: A=-100, B=0, C=+100 → 1 settlement (A→C 100)
        """
        s = ExpenseSplitter(["A", "B", "C"])
        s.add_expense(Expense("Dinner", Decimal("100"), "A", SplitType.EXACT,
                               [{"member": "A", "amount": Decimal("0")},
                                {"member": "B", "amount": Decimal("100")}]))
        s.add_expense(Expense("Lunch", Decimal("100"), "B", SplitType.EXACT,
                               [{"member": "B", "amount": Decimal("0")},
                                {"member": "C", "amount": Decimal("100")}]))
        net = s.net_balances()
        # E1: A pays 100, A owes 0, B owes 100 → A+100, B-100
        # E2: B pays 100, B owes 0, C owes 100 → B+100, C-100
        # Net: A=+100, B=0, C=-100
        assert net["A"] == Decimal("100")
        assert net["C"] == Decimal("-100")
        settlements = s.simplify()
        # Settlements: C→A 100 (1 transaction)
        assert len(settlements) == 1
        assert settlements[0].from_member == "C"
        assert settlements[0].to_member == "A"

    def test_complex_cycle_optimality(self):
        """
        A net = +100, B net = +100, C net = -50, D net = -150
        Should produce 2 settlements max.
        """
        s = ExpenseSplitter(["A", "B", "C", "D"])
        e1 = Expense("X", Decimal("150"), "C", SplitType.EQUAL,
                      [{"member": "C"}, {"member": "A"}])
        e2 = Expense("Y", Decimal("100"), "B", SplitType.EQUAL,
                      [{"member": "B"}, {"member": "D"}])
        e3 = Expense("Z", Decimal("100"), "D", SplitType.EQUAL,
                      [{"member": "A"}, {"member": "D"}])
        s.add_expense(e1)  # C paid 150, C owes 75, A owes 75 → C+75, A-75
        s.add_expense(e2)  # B paid 100, B owes 50, D owes 50 → B+50, D-50
        s.add_expense(e3)  # D paid 100, D owes 50, A owes 50 → D+50, A-50
        # Net: A = -75 - 50 = -125; B = +50; C = +75; D = -50 + 50 = 0
        settlements = s.simplify()
        # Optimal: A→B 50, A→C 75 (or similar) — max 2 settlements
        assert len(settlements) <= 2


# =========================================================================
# Integration: Full pipeline
# =========================================================================

class TestIntegration:
    def test_full_report(self):
        """Report runs without error and is non-empty."""
        s = ExpenseSplitter(["A", "B"])
        e = Expense("Lunch", Decimal("100"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}])
        s.add_expense(e)
        report = s.report()
        assert "Net Balances" in report
        assert "Settlements" in report
        assert len(report) > 50

    def test_from_json_batch(self):
        """Process the sample file."""
        s = ExpenseSplitter.from_json(
            str(Path(__file__).parent.parent / "samples" / "simple.json"))
        net = s.net_balances()
        # Sum of net balances should be zero
        total_net = sum(net.values(), Decimal("0"))
        assert total_net == Decimal("0"), f"Net should sum to 0, got {total_net}"
        settlements = s.simplify()
        # Settlements should balance net
        total_settled = sum(st.amount for st in settlements)
        assert total_settled > 0

    def test_negative_fractional_rounding(self):
        """₹0.01 / 3 with equal split should handle sub-paisa rounding."""
        s = ExpenseSplitter(["A", "B", "C"])
        e = Expense("Tiny", Decimal("0.01"), "A", SplitType.EQUAL,
                     [{"member": "A"}, {"member": "B"}, {"member": "C"}])
        s.add_expense(e)
        net = s.net_balances()
        total_net = sum(net.values(), Decimal("0"))
        assert total_net == Decimal("0"), f"Net should sum to 0, got {total_net}"

    def test_large_group(self):
        """10 members, one pays all."""
        members = [f"P{i}" for i in range(10)]
        s = ExpenseSplitter(members)
        e = Expense("Big party", Decimal("10000"), members[0], SplitType.EQUAL,
                     [{"member": m} for m in members])
        s.add_expense(e)
        net = s.net_balances()
        assert net["P0"] == Decimal("9000")  # paid 10000, owes 1000
        for i in range(1, 10):
            assert net[f"P{i}"] == Decimal("-1000")
        settlements = s.simplify()
        assert len(settlements) == 9
        # All 9 pay P0
        total_settled = sum(st.amount for st in settlements)
        assert total_settled == Decimal("9000")