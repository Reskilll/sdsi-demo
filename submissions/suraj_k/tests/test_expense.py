"""
Tests for the Expense value object.
"""

import unittest
from decimal import Decimal

from src.models.expense import Expense
from src.models.member import Member
from src.models.split import EqualSplit


class TestExpense(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")

    def test_expense_creation(self):
        split = EqualSplit([self.alice, self.bob], Decimal("42.50"))
        expense = Expense("Coffee", self.alice, Decimal("42.50"), split)
        self.assertEqual(expense.description, "Coffee")
        self.assertEqual(expense.total_amount, Decimal("42.50"))
        self.assertIsNotNone(expense.id)
        self.assertEqual(len(expense.id), 32)  # UUID hex

    def test_expense_stores_created_at(self):
        split = EqualSplit([self.alice, self.bob], Decimal("10"))
        expense = Expense("Snack", self.alice, Decimal("10"), split)
        self.assertIsNotNone(expense.created_at)

    def test_two_expenses_have_different_ids(self):
        split = EqualSplit([self.alice, self.bob], Decimal("10"))
        e1 = Expense("A", self.alice, Decimal("10"), split)
        e2 = Expense("B", self.bob, Decimal("10"), split)
        self.assertNotEqual(e1.id, e2.id)

    def test_large_amount(self):
        split = EqualSplit([self.alice, self.bob], Decimal("9999999.99"))
        expense = Expense("Big", self.alice, Decimal("9999999.99"), split)
        self.assertEqual(expense.total_amount, Decimal("9999999.99"))


if __name__ == "__main__":
    unittest.main()