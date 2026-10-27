"""Comprehensive test suite for the Expense Splitter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the package importable without installing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expense_splitter.models import SplitType
from expense_splitter.validation import (
    validate_expense,
    validate_expense_full,
    validate_expenses,
)
from expense_splitter.balance import compute_balances
from expense_splitter.simplify import simplify
from expense_splitter.processor import process

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _exp(**kw):
    from expense_splitter.models import Expense
    defaults = dict(
        description="test",
        paid_by="A",
        total_amount=100.0,
        split_type=SplitType.EQUAL,
        participants=["A", "B"],
        splits={},
    )
    defaults.update(kw)
    return Expense(**defaults)


# ---------------------------------------------------------------------------
#  Validation  (M5)
# ---------------------------------------------------------------------------

class TestValidateExpense:
    """M5: percentages sum to 100, exact amounts sum to total, payer in group."""

    def test_equal_ok(self):
        assert validate_expense(_exp()) is None

    def test_payer_not_in_participants(self):
        err = validate_expense(_exp(paid_by="X", participants=["A", "B"]))
        assert err and "not a participant" in err

    def test_empty_participants(self):
        err = validate_expense(_exp(participants=[]))
        assert err and "at least one participant" in err

    def test_negative_total(self):
        err = validate_expense(_exp(total_amount=-50))
        assert err and "negative" in err

    def test_exact_ok(self):
        err = validate_expense(
            _exp(
                split_type=SplitType.EXACT,
                total_amount=100,
                splits={"A": 60, "B": 40},
            )
        )
        assert err is None

    def test_exact_sum_mismatch(self):
        err = validate_expense(
            _exp(
                split_type=SplitType.EXACT,
                total_amount=100,
                splits={"A": 50, "B": 40},
            )
        )
        assert err and "do not sum to total" in err

    def test_exact_negative_split(self):
        err = validate_expense(
            _exp(
                split_type=SplitType.EXACT,
                total_amount=100,
                splits={"A": -10, "B": 110},
            )
        )
        assert err and "negative" in err

    def test_percentage_ok(self):
        err = validate_expense(
            _exp(
                split_type=SplitType.PERCENTAGE,
                total_amount=200,
                splits={"A": 60, "B": 40},
            )
        )
        assert err is None

    def test_percentage_sum_not_100(self):
        err = validate_expense(
            _exp(
                split_type=SplitType.PERCENTAGE,
                total_amount=100,
                splits={"A": 70, "B": 20},
            )
        )
        assert err and "100%" in err

    def test_equal_split_with_splits_rejected(self):
        err = validate_expense(
            _exp(split_type=SplitType.EQUAL, splits={"A": 50})
        )
        assert err and "must not provide" in err

    def test_exact_missing_participants_warning(self):
        """Missing exact-split participants → soft warning, no hard error."""
        err, warn = validate_expense_full(
            _exp(
                split_type=SplitType.EXACT,
                total_amount=100,
                participants=["A", "B"],
                splits={"A": 100},
            )
        )
        assert err is None
        assert warn and "missing amounts" in warn

    def test_percentage_missing_participants_warning(self):
        """Missing percentage-split participants → soft warning, no hard error."""
        err, warn = validate_expense_full(
            _exp(
                split_type=SplitType.PERCENTAGE,
                total_amount=100,
                participants=["A", "B"],
                splits={"A": 100},
            )
        )
        assert err is None
        assert warn and "missing values" in warn

    def test_duplicate_participants_deduped(self):
        """Duplicate participants should be deduplicated — payer check still passes."""
        err = validate_expense(
            _exp(paid_by="A", participants=["A", "A", "B"])
        )
        assert err is None

    def test_zero_total_equal_split(self):
        err = validate_expense(_exp(total_amount=0))
        assert err is None  # 0 divided equally is fine

    def test_splits_nonequal_split_type_key(self):
        err = validate_expense(_exp(split_type="invalid"))
        assert err and "unknown split_type" in err


class TestBatchValidate:
    """Batch validation (validate_expenses)."""

    def test_empty_list(self):
        errs = validate_expenses([])
        assert "empty" in errs[0].lower()

    def test_not_a_list(self):
        errs = validate_expenses({"a": 1})
        assert len(errs) == 1

    def test_mixed_valid_invalid(self):
        data = [
            {"description": "ok", "paid_by": "A", "total_amount": 100,
             "split_type": "equal", "participants": ["A", "B"]},
            {"description": "bad", "paid_by": "X", "total_amount": 100,
             "split_type": "equal", "participants": ["A", "B"]},
        ]
        errs = validate_expenses(data)
        assert len(errs) == 1
        assert "X" in errs[0]

    def test_non_dict_entry(self):
        errs = validate_expenses(["not a dict"])
        assert len(errs) == 1
        assert "not a JSON object" in errs[0]


# ---------------------------------------------------------------------------
#  Balance computation  (M2)
# ---------------------------------------------------------------------------

class TestBalances:
    def test_simple_equal(self):
        expenses = [
            _exp(paid_by="A", total_amount=100, participants=["A", "B"]),
        ]
        b = compute_balances(expenses)
        assert b["A"] == pytest.approx(50.0)
        assert b["B"] == pytest.approx(-50.0)

    def test_everyone_pays_own_share(self):
        """A pays 40, B pays 60 → everything balanced."""
        expenses = [
            _exp(
                paid_by="A", total_amount=40,
                split_type=SplitType.EXACT,
                participants=["A", "B"],
                splits={"A": 40, "B": 0},
            ),
            _exp(
                paid_by="B", total_amount=60,
                split_type=SplitType.EXACT,
                participants=["A", "B"],
                splits={"A": 0, "B": 60},
            ),
        ]
        b = compute_balances(expenses)
        for v in b.values():
            assert abs(v) < 0.01

    def test_percentage_split(self):
        expenses = [
            _exp(
                paid_by="A", total_amount=200,
                split_type=SplitType.PERCENTAGE,
                participants=["A", "B", "C"],
                splits={"A": 50, "B": 30, "C": 20},
            ),
        ]
        b = compute_balances(expenses)
        # A paid 200, owes 100 → net +100
        assert b["A"] == pytest.approx(100.0)
        # B owes 60
        assert b["B"] == pytest.approx(-60.0)
        # C owes 40
        assert b["C"] == pytest.approx(-40.0)

    def test_sum_zero(self):
        expenses = [
            _exp(paid_by="A", total_amount=150, participants=["A", "B", "C"]),
            _exp(paid_by="B", total_amount=300, participants=["A", "B", "C"]),
        ]
        b = compute_balances(expenses)
        assert sum(b.values()) == pytest.approx(0.0, abs=0.02)


# ---------------------------------------------------------------------------
#  Settlement simplification  (M3)
# ---------------------------------------------------------------------------

class TestSimplify:
    def test_already_balanced(self):
        assert simplify({"A": 0, "B": 0}) == []

    def test_single_settlement(self):
        s = simplify({"A": 50, "B": -50})
        assert len(s) == 1
        assert s[0].from_member == "B"
        assert s[0].to_member == "A"
        assert s[0].amount == 50

    def test_cycle_simplified(self):
        """A→B→C→A cycle should collapse to at most 2 transactions."""
        # A owes B 10, B owes C 10, C owes A 10 — net zero each.
        s = simplify({"A": 0, "B": 0, "C": 0})
        assert s == []

    def test_multi_creditor_debtor(self):
        """A: +100, B: +50, C: -70, D: -80 → 3 txns max."""
        s = simplify({"A": 100, "B": 50, "C": -70, "D": -80})
        assert len(s) <= 3
        total_flow = sum(tx.amount for tx in s)
        assert total_flow == pytest.approx(150.0)

    def test_floating_point_noise_ignored(self):
        s = simplify({"A": 0.001, "B": -0.001})
        assert s == []

    def test_three_way(self):
        s = simplify({"A": 100, "B": -60, "C": -40})
        assert len(s) == 2
        flows = {tx.amount for tx in s}
        assert flows == {60, 40}


# ---------------------------------------------------------------------------
#  Processor  (full pipeline)
# ---------------------------------------------------------------------------

class TestProcessor:
    def test_happy_path(self):
        data = [
            {"description": "Dinner", "paid_by": "Alice", "total_amount": 300,
             "split_type": "equal", "participants": ["Alice", "Bob", "Charlie"]},
        ]
        result = process(data)
        assert result.expenses_processed == 1
        assert "Alice" in result.balances
        assert abs(sum(result.balances.values())) < 0.02
        assert len(result.settlements) == 2

    def test_not_list(self):
        result = process({})
        assert result.expenses_processed == 0
        assert "must be a JSON array" in result.errors[0]

    def test_mixed_valid_invalid(self):
        data = [
            {"description": "ok", "paid_by": "A", "total_amount": 100,
             "split_type": "equal", "participants": ["A", "B"]},
            "not an object",
            {"description": "bad", "paid_by": "X", "total_amount": 100,
             "split_type": "equal", "participants": ["A"]},
        ]
        result = process(data)
        assert result.expenses_processed == 1
        assert any("not a JSON object" in e for e in result.errors)
        assert result.balances

    def test_percentage_ok(self):
        data = [
            {"description": "Lunch", "paid_by": "A", "total_amount": 500,
             "split_type": "percentage", "participants": ["A", "B"],
             "splits": {"A": 40, "B": 60}},
        ]
        result = process(data)
        assert result.expenses_processed == 1
        assert result.balances["A"] == pytest.approx(300.0, abs=0.02)


# ---------------------------------------------------------------------------
#  Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_amount_expense(self):
        result = process([
            {"description": "freebie", "paid_by": "A", "total_amount": 0,
             "split_type": "equal", "participants": ["A", "B"]},
        ])
        assert result.expenses_processed == 1
        assert result.balances["A"] == pytest.approx(0)
        assert result.balances["B"] == pytest.approx(0)
        assert result.settlements == []

    def test_single_participant(self):
        """A person can split with themselves (lone outing)."""
        result = process([
            {"description": "solo coffee", "paid_by": "A", "total_amount": 80,
             "split_type": "equal", "participants": ["A"]},
        ])
        assert result.expenses_processed == 1
        assert result.balances["A"] == pytest.approx(0)
        assert result.settlements == []

    def test_all_same_payer(self):
        result = process([
            {"description": "e1", "paid_by": "A", "total_amount": 100,
             "split_type": "equal", "participants": ["A", "B"]},
            {"description": "e2", "paid_by": "A", "total_amount": 200,
             "split_type": "equal", "participants": ["A", "B"]},
        ])
        assert result.balances["A"] == pytest.approx(150.0)
        assert result.balances["B"] == pytest.approx(-150.0)

    def test_unicode_names(self):
        result = process([
            {"description": "🍕 pizza", "paid_by": "José", "total_amount": 50,
             "split_type": "equal", "participants": ["José", "Clément"]},
        ])
        assert result.expenses_processed == 1

    def test_floating_total(self):
        result = process([
            {"description": "snacks", "paid_by": "A", "total_amount": 10.33,
             "split_type": "equal", "participants": ["A", "B", "C"]},
        ])
        assert result.expenses_processed == 1
        assert sum(result.balances.values()) == pytest.approx(0, abs=0.02)

    def test_percentage_rounding(self):
        """33/33/34 sums to 100 but produces fractional shares."""
        result = process([
            {"description": "rounding", "paid_by": "A", "total_amount": 100,
             "split_type": "percentage", "participants": ["A", "B", "C"],
             "splits": {"A": 33, "B": 33, "C": 34}},
        ])
        assert result.expenses_processed == 1
        assert sum(result.balances.values()) == pytest.approx(0, abs=0.02)

    def test_many_expenses_batch(self):
        data = [
            {"description": f"e{i}", "paid_by": "A", "total_amount": 10,
             "split_type": "equal", "participants": ["A", "B"]}
            for i in range(100)
        ]
        result = process(data)
        assert result.expenses_processed == 100

    def test_large_amount(self):
        result = process([
            {"description": "big", "paid_by": "A", "total_amount": 1e9,
             "split_type": "equal", "participants": ["A", "B"]},
        ])
        assert result.expenses_processed == 1
        assert result.balances["A"] == pytest.approx(5e8)

    def test_missing_description_rejected(self):
        """Empty description (from missing key) → hard error, not processed."""
        result = process([
            {"paid_by": "A", "total_amount": 50, "split_type": "equal",
             "participants": ["A", "B"]},
        ])
        assert result.expenses_processed == 0
        assert result.errors and any(
            "description" in e.lower() for e in result.errors
        )