#!/usr/bin/env python3
"""
Tests for Expense Splitter.

Run: python -m pytest test_expense_splitter.py -v
Or:  python test_expense_splitter.py
"""

import json
import os
import sys
import unittest

# Ensure the module is importable from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from expense_splitter import (
    Expense,
    ValidationError,
    validate_expense,
    compute_net_balances,
    simplify_debts,
    process_group,
    process_batch,
    _to_decimal,
)
from decimal import Decimal


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.group = ["Alice", "Bob", "Charlie"]

    def test_missing_fields(self):
        with self.assertRaises(ValidationError):
            validate_expense({}, self.group)

    def test_missing_total(self):
        with self.assertRaises(ValidationError):
            validate_expense({"paid_by": "A", "split_type": "equal"}, self.group)

    def test_invalid_split_type(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "invalid",
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_negative_total(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": -100,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_payer_not_in_group(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Stranger",
                    "split_type": "equal",
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_member_not_in_group(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Alice", "Stranger"],
                },
                self.group,
            )

    def test_exact_sum_mismatch(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "exact",
                    "shares": {"Alice": 50, "Bob": 30},
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_percentage_not_100(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "percentage",
                    "shares": {"Alice": 50, "Bob": 30},
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_percentage_negative(self):
        with self.assertRaises(ValidationError):
            validate_expense(
                {
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "percentage",
                    "shares": {"Alice": -10, "Bob": 110},
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )

    def test_valid_equal(self):
        try:
            validate_expense(
                {
                    "total_amount": 300,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Alice", "Bob", "Charlie"],
                },
                self.group,
            )
        except ValidationError as e:
            self.fail(f"Unexpected error: {e}")

    def test_valid_exact(self):
        try:
            validate_expense(
                {
                    "total_amount": 300,
                    "paid_by": "Alice",
                    "split_type": "exact",
                    "shares": {"Alice": 100, "Bob": 200},
                    "members": ["Alice", "Bob"],
                },
                self.group,
            )
        except ValidationError as e:
            self.fail(f"Unexpected error: {e}")

    def test_valid_percentage(self):
        try:
            validate_expense(
                {
                    "total_amount": 200,
                    "paid_by": "Alice",
                    "split_type": "percentage",
                    "shares": {"Alice": 60, "Bob": 25, "Charlie": 15},
                    "members": ["Alice", "Bob", "Charlie"],
                },
                self.group,
            )
        except ValidationError as e:
            self.fail(f"Unexpected error: {e}")


class TestExpenseFromDict(unittest.TestCase):
    def test_equal_split(self):
        data = {
            "title": "Lunch",
            "total_amount": 300,
            "paid_by": "Alice",
            "split_type": "equal",
            "members": ["Alice", "Bob", "Charlie"],
        }
        exp = Expense.from_dict(data)
        self.assertEqual(exp.total_amount, Decimal("300"))
        self.assertEqual(exp.shares["Alice"], Decimal("100"))
        self.assertEqual(exp.shares["Bob"], Decimal("100"))
        self.assertEqual(exp.shares["Charlie"], Decimal("100"))

    def test_exact_split(self):
        data = {
            "title": "Dinner",
            "total_amount": 500,
            "paid_by": "Bob",
            "split_type": "exact",
            "shares": {"Alice": 200, "Bob": 150, "Charlie": 150},
            "members": ["Alice", "Bob", "Charlie"],
        }
        exp = Expense.from_dict(data)
        self.assertEqual(exp.shares["Alice"], Decimal("200"))
        self.assertEqual(exp.shares["Bob"], Decimal("150"))

    def test_percentage_split(self):
        data = {
            "title": "Party",
            "total_amount": 1000,
            "paid_by": "Charlie",
            "split_type": "percentage",
            "shares": {"Alice": 50, "Bob": 30, "Charlie": 20},
            "members": ["Alice", "Bob", "Charlie"],
        }
        exp = Expense.from_dict(data)
        self.assertEqual(exp.shares["Alice"], Decimal("500"))
        self.assertEqual(exp.shares["Bob"], Decimal("300"))
        self.assertEqual(exp.shares["Charlie"], Decimal("200"))

    def test_float_input(self):
        data = {
            "title": "Test",
            "total_amount": 99.99,
            "paid_by": "Alice",
            "split_type": "equal",
            "members": ["Alice", "Bob"],
        }
        exp = Expense.from_dict(data)
        self.assertEqual(exp.total_amount, Decimal("99.99"))
        # Alice (first) gets remainder, Bob gets rounded half
        self.assertEqual(float(exp.shares["Alice"]), 50.00)
        self.assertAlmostEqual(float(exp.shares["Bob"]), 49.99)


class TestNetBalances(unittest.TestCase):
    def test_simple(self):
        expenses = [
            Expense(
                title="Lunch",
                total_amount=Decimal("300"),
                paid_by="Alice",
                split_type="equal",
                shares={"Alice": Decimal("100"), "Bob": Decimal("100"), "Charlie": Decimal("100")},
                members=["Alice", "Bob", "Charlie"],
            )
        ]
        balances = compute_net_balances(expenses)
        # Alice paid 300, owes 100 → net +200
        # Bob paid 0, owes 100 → net -100
        # Charlie paid 0, owes 100 → net -100
        self.assertEqual(balances["Alice"], Decimal("200"))
        self.assertEqual(balances["Bob"], Decimal("-100"))
        self.assertEqual(balances["Charlie"], Decimal("-100"))

    def test_multiple_expenses(self):
        expenses = [
            Expense(
                title="Dinner",
                total_amount=Decimal("6000"),
                paid_by="Alice",
                split_type="equal",
                shares={
                    "Alice": Decimal("1500"),
                    "Bob": Decimal("1500"),
                    "Charlie": Decimal("1500"),
                    "Diana": Decimal("1500"),
                },
                members=["Alice", "Bob", "Charlie", "Diana"],
            ),
            Expense(
                title="Tickets",
                total_amount=Decimal("1500"),
                paid_by="Bob",
                split_type="exact",
                shares={"Alice": Decimal("500"), "Bob": Decimal("500"), "Charlie": Decimal("500")},
                members=["Alice", "Bob", "Charlie"],
            ),
        ]
        balances = compute_net_balances(expenses)
        # Alice: +6000 (paid) - 1500 (dinner share) - 500 (tickets) = +4000
        # Actually wait: Alice paid 6000 for dinner. Bob paid 1500 for tickets.
        # Dinner: Alice paid 6000, share 1500 each
        # Tickets: Bob paid 1500, shares: Alice 500, Bob 500, Charlie 500
        # Alice: +6000 - 1500 - 500 = 4000
        # Bob: +1500 - 1500 - 500 = -500
        # Charlie: 0 - 1500 - 500 = -2000
        # Diana: 0 - 1500 = -1500
        self.assertEqual(balances["Alice"], Decimal("4000"))
        self.assertEqual(balances["Bob"], Decimal("-500"))
        self.assertEqual(balances["Charlie"], Decimal("-2000"))
        self.assertEqual(balances["Diana"], Decimal("-1500"))


class TestDebtSimplification(unittest.TestCase):
    def test_simple_settlement(self):
        balances = {
            "Alice": Decimal("200"),
            "Bob": Decimal("-100"),
            "Charlie": Decimal("-100"),
        }
        settlements = simplify_debts(balances)
        # Should produce 2 transactions
        self.assertTrue(len(settlements) >= 2)

        # Verify total amounts match
        total_owed = sum(a for _, _, a in settlements)
        self.assertAlmostEqual(float(total_owed), 200.0, places=1)

    def test_no_debts(self):
        balances = {"Alice": Decimal("0"), "Bob": Decimal("0")}
        settlements = simplify_debts(balances)
        self.assertEqual(len(settlements), 0)

    def test_zero_balance_person(self):
        balances = {
            "Alice": Decimal("100"),
            "Bob": Decimal("-100"),
            "Charlie": Decimal("0"),
        }
        settlements = simplify_debts(balances)
        # Charlie should not appear in settlements
        involved = {s[0] for s in settlements} | {s[1] for s in settlements}
        self.assertNotIn("Charlie", involved)

    def test_settlement_accuracy(self):
        balances = {
            "A": Decimal("250"),
            "B": Decimal("-150"),
            "C": Decimal("-100"),
        }
        settlements = simplify_debts(balances)
        # Total paid = total owed
        total_from = sum(a for _, _, a in settlements)
        self.assertAlmostEqual(float(total_from), 250.0, places=1)


class TestEndToEnd(unittest.TestCase):
    def test_sample_data(self):
        result = process_group(
            group_name="Team Outing",
            members=["Alice", "Bob", "Charlie", "Diana"],
            expenses_data=[
                {
                    "title": "Dinner",
                    "total_amount": 6000,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Alice", "Bob", "Charlie", "Diana"],
                },
                {
                    "title": "Movie Tickets",
                    "total_amount": 1500,
                    "paid_by": "Bob",
                    "split_type": "exact",
                    "shares": {"Alice": 500, "Bob": 500, "Charlie": 500},
                    "members": ["Alice", "Bob", "Charlie"],
                },
            ],
        )
        self.assertEqual(result["group"], "Team Outing")
        self.assertEqual(len(result["expenses"]), 2)
        self.assertIn("balances", result)
        self.assertIn("settlements", result)
        # Verify balances make sense
        self.assertAlmostEqual(
            sum(result["balances"].values()), 0.0, places=10
        )

    def test_batch_processing(self):
        data = {
            "groups": [
                {
                    "name": "Group1",
                    "members": ["A", "B"],
                    "expenses": [
                        {
                            "title": "Lunch",
                            "total_amount": 100,
                            "paid_by": "A",
                            "split_type": "equal",
                            "members": ["A", "B"],
                        }
                    ],
                },
                {
                    "name": "Group2",
                    "members": ["X", "Y"],
                    "expenses": [
                        {
                            "title": "Dinner",
                            "total_amount": 200,
                            "paid_by": "X",
                            "split_type": "equal",
                            "members": ["X", "Y"],
                        }
                    ],
                },
            ]
        }
        result = process_batch(data)
        self.assertEqual(len(result["results"]), 2)

    def test_sample_json_file(self):
        """Test loading from the shipped sample file."""
        sample_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "samples",
            "expenses.json",
        )
        with open(sample_path) as f:
            data = json.load(f)
        result = process_group(
            group_name="Sample Group",
            members=["Alice", "Bob", "Charlie"],
            expenses_data=data,
        )
        self.assertIn("balances", result)
        self.assertIn("settlements", result)
        # Net sum of balances should be zero
        self.assertAlmostEqual(
            sum(result["balances"].values()), 0.0, places=10
        )


class TestEdgeCases(unittest.TestCase):
    def test_single_person(self):
        """A group with one person — no debts."""
        result = process_group(
            group_name="Solo",
            members=["Alice"],
            expenses_data=[
                {
                    "title": "Lunch",
                    "total_amount": 100,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Alice"],
                }
            ],
        )
        self.assertEqual(result["balances"]["Alice"], 0.0)
        self.assertEqual(len(result["settlements"]), 0)

    def test_payer_not_in_members_equal(self):
        """Equal split where payer isn't in members list should still work."""
        result = process_group(
            group_name="Test",
            members=["Alice", "Bob", "Charlie"],
            expenses_data=[
                {
                    "title": "Dinner",
                    "total_amount": 300,
                    "paid_by": "Alice",
                    "split_type": "equal",
                    "members": ["Bob", "Charlie"],
                }
            ],
        )
        # Alice paid 300, split 3 ways (Alice, Bob, Charlie) = 100 each
        # Alice owes 100, paid 300 → net +200
        # Bob owes 100, paid 0 → net -100
        # Charlie owes 100, paid 0 → net -100
        self.assertEqual(result["balances"]["Alice"], 200.0)
        self.assertEqual(result["balances"]["Bob"], -100.0)
        self.assertEqual(result["balances"]["Charlie"], -100.0)

    def test_rounding_edge(self):
        """Amounts that don't divide evenly (e.g., 100 split 3 ways)."""
        result = process_group(
            group_name="RoundTest",
            members=["A", "B", "C"],
            expenses_data=[
                {
                    "title": "Pizza",
                    "total_amount": 100,
                    "paid_by": "A",
                    "split_type": "equal",
                    "members": ["A", "B", "C"],
                }
            ],
        )
        # 100/3 = 33.33... each
        total_shares = sum(result["balances"].values())
        self.assertAlmostEqual(total_shares, 0.0, places=10)

    def test_invalid_batch_member(self):
        data = {
            "groups": [
                {
                    "name": "Bad",
                    "members": ["A", "B"],
                    "expenses": [
                        {
                            "title": "Test",
                            "total_amount": 100,
                            "paid_by": "A",
                            "split_type": "equal",
                            "members": ["A", "Z"],  # Z not in group
                        }
                    ],
                }
            ]
        }
        with self.assertRaises(ValidationError):
            process_batch(data)


if __name__ == "__main__":
    unittest.main()