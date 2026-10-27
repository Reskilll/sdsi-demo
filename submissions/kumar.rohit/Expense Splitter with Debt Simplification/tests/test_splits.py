"""
Tests for split calculation (equal, exact, percentage).
"""

from decimal import Decimal

import pytest

from expense_splitter.models import Expense, SplitEntry, SplitType
from expense_splitter.splits import compute_shares


def make_expense(**kwargs) -> Expense:
    defaults = {
        "expense_id": "e1",
        "description": "test",
        "amount": Decimal("100.00"),
        "currency": "INR",
        "payer_id": "a",
        "participant_ids": ("a", "b", "c"),
        "split_type": SplitType.EQUAL,
        "split_details": (),
    }
    defaults.update(kwargs)
    return Expense(**defaults)


class TestEqualSplit:
    """Equal split test cases."""

    def test_equal_split_three_ways(self):
        """₹100 split among 3 people."""
        exp = make_expense(amount=Decimal("100.00"), participant_ids=("a", "b", "c"))
        shares = compute_shares(exp)
        assert shares.shares["a"] + shares.shares["b"] + shares.shares["c"] == Decimal("100.00")
        # One person gets 33.34, two get 33.33
        values = sorted(shares.shares.values())
        assert values == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]

    def test_equal_split_exact_division(self):
        """₹90 split among 3 people – exact division no remainder."""
        exp = make_expense(amount=Decimal("90.00"), participant_ids=("a", "b", "c"))
        shares = compute_shares(exp)
        for v in shares.shares.values():
            assert v == Decimal("30.00")

    def test_equal_split_two_people(self):
        """₹100 split among 2 people."""
        exp = make_expense(amount=Decimal("100.00"), participant_ids=("a", "b"))
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("50.00")
        assert shares.shares["b"] == Decimal("50.00")

    def test_equal_split_one_person(self):
        """One participant – gets the full amount."""
        exp = make_expense(amount=Decimal("500.00"), participant_ids=("a",))
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("500.00")

    def test_equal_split_very_small_amount(self):
        """₹0.01 split among 3 people."""
        exp = make_expense(amount=Decimal("0.01"), participant_ids=("a", "b", "c"))
        shares = compute_shares(exp)
        total = sum(shares.shares.values())
        assert total == Decimal("0.01")

    def test_equal_split_large_amount(self):
        """Large amounts should still be exact."""
        exp = make_expense(amount=Decimal("9999999.99"), participant_ids=("a", "b", "c"))
        shares = compute_shares(exp)
        total = sum(shares.shares.values())
        assert total == Decimal("9999999.99")

    def test_equal_split_total_equals_amount(self):
        """Multiple random splits: total always equals expense amount."""
        import random
        random.seed(42)
        for _ in range(50):
            n = random.randint(2, 10)
            amt = Decimal(str(round(random.uniform(1, 10000), 2))).quantize(Decimal("0.01"))
            pids = tuple(f"m{i}" for i in range(n))
            exp = make_expense(expense_id="rand", amount=amt, participant_ids=pids)
            shares = compute_shares(exp)
            total = sum(shares.shares.values())
            assert total == amt, f"Failed for {amt} with {n} participants: total={total}"

    def test_deterministic_output(self):
        """Same input always gives same output."""
        exp = make_expense(amount=Decimal("100.00"), participant_ids=("a", "b", "c"))
        shares1 = compute_shares(exp)
        shares2 = compute_shares(exp)
        assert shares1.shares == shares2.shares


class TestExactSplit:
    """Exact split test cases."""

    def test_exact_split_simple(self):
        exp = make_expense(
            amount=Decimal("1000.00"),
            participant_ids=("a", "b", "c"),
            split_type=SplitType.EXACT,
            split_details=(
                SplitEntry("a", Decimal("200")),
                SplitEntry("b", Decimal("300")),
                SplitEntry("c", Decimal("500")),
            ),
        )
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("200.00")
        assert shares.shares["b"] == Decimal("300.00")
        assert shares.shares["c"] == Decimal("500.00")
        assert sum(shares.shares.values()) == Decimal("1000.00")

    def test_exact_split_with_paise(self):
        exp = make_expense(
            amount=Decimal("100.50"),
            participant_ids=("a", "b"),
            split_type=SplitType.EXACT,
            split_details=(
                SplitEntry("a", Decimal("40.25")),
                SplitEntry("b", Decimal("60.25")),
            ),
        )
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("40.25")
        assert shares.shares["b"] == Decimal("60.25")


class TestPercentageSplit:
    """Percentage split test cases."""

    def test_percentage_split_simple(self):
        exp = make_expense(
            amount=Decimal("1000.00"),
            participant_ids=("a", "b", "c"),
            split_type=SplitType.PERCENTAGE,
            split_details=(
                SplitEntry("a", Decimal("20")),
                SplitEntry("b", Decimal("30")),
                SplitEntry("c", Decimal("50")),
            ),
        )
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("200.00")
        assert shares.shares["b"] == Decimal("300.00")
        assert shares.shares["c"] == Decimal("500.00")
        assert sum(shares.shares.values()) == Decimal("1000.00")

    def test_percentage_split_rounding(self):
        """₹100 split 3-way by percentage (33.33%, 33.33%, 33.34% → 100%)."""
        exp = make_expense(
            amount=Decimal("100.00"),
            participant_ids=("a", "b", "c"),
            split_type=SplitType.PERCENTAGE,
            split_details=(
                SplitEntry("a", Decimal("33.33")),
                SplitEntry("b", Decimal("33.33")),
                SplitEntry("c", Decimal("33.34")),
            ),
        )
        shares = compute_shares(exp)
        total = sum(shares.shares.values())
        assert total == Decimal("100.00")

    def test_percentage_0_percent(self):
        """A participant with 0% share."""
        exp = make_expense(
            amount=Decimal("500.00"),
            participant_ids=("a", "b"),
            split_type=SplitType.PERCENTAGE,
            split_details=(
                SplitEntry("a", Decimal("100")),
                SplitEntry("b", Decimal("0")),
            ),
        )
        shares = compute_shares(exp)
        assert shares.shares["a"] == Decimal("500.00")
        assert shares.shares["b"] == Decimal("0.00")

    def test_percentage_large_expense_rounding(self):
        """Verify rounding preserves total for percentage splits."""
        import random
        random.seed(123)
        for _ in range(50):
            n = random.randint(2, 5)
            amt = Decimal(str(round(random.uniform(1, 9999), 2))).quantize(Decimal("0.01"))

            # Generate percentages that sum to 100
            parts = sorted([random.random() for _ in range(n)])
            raw_pcts = []
            prev = 0
            for i in range(n - 1):
                raw_pcts.append((parts[i + 1] - parts[i]) * 100)
            raw_pcts.append((1 - parts[-1]) * 100)
            # Round to 2 decimals
            pcts = [Decimal(str(round(p, 2))) for p in raw_pcts]
            # Adjust so they sum to 100
            diff = Decimal("100") - sum(pcts)
            if diff != 0:
                pcts[0] += diff

            entries = tuple(SplitEntry(f"m{i}", pcts[i]) for i in range(n))
            exp = make_expense(
                expense_id=f"pct_{_}",
                amount=amt,
                participant_ids=tuple(f"m{i}" for i in range(n)),
                split_type=SplitType.PERCENTAGE,
                split_details=entries,
            )
            shares = compute_shares(exp)
            total = sum(shares.shares.values())
            assert total == amt, f"Total mismatch: {total} != {amt}, pcts={pcts}"


class TestMoneyRounding:
    """Money & rounding specific tests."""

    def test_split_100_among_3(self):
        """Specifically test ₹100 among 3 people."""
        exp = make_expense(amount=Decimal("100.00"), participant_ids=("a", "b", "c"))
        shares = compute_shares(exp)
        values = list(shares.shares.values())
        assert sum(values) == Decimal("100.00")
        assert values.count(Decimal("33.33")) == 2
        assert values.count(Decimal("33.34")) == 1

    def test_repeated_decimal_expenses(self):
        """Multiple expenses with decimal amounts accumulate correctly."""
        # This tests that repeated cent-level rounding doesn't drift
        total = Decimal("0")
        for i in range(100):
            exp = make_expense(
                expense_id=f"r{i}",
                amount=Decimal("0.01"),
                participant_ids=("a", "b"),
            )
            shares = compute_shares(exp)
            total += sum(shares.shares.values())
        assert total == Decimal("1.00")

    def test_no_floating_point_used(self):
        """Verify all amounts are Decimal, not float."""
        exp = make_expense(amount=Decimal("50.00"), participant_ids=("a", "b"))
        shares = compute_shares(exp)
        for v in shares.shares.values():
            assert isinstance(v, Decimal)
            # Should not be a float-converted Decimal
            assert v == Decimal("25.00")