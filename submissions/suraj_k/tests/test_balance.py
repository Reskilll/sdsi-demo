"""
Tests for BalanceCalculator — net position computation.
Includes Edge Cases 1 (residue), 4 (self-payment), and 5 (inactive member in history).
"""

import unittest
from decimal import Decimal

from src.models.expense import Expense
from src.models.member import Member
from src.models.split import EqualSplit, ExactSplit, PercentageSplit
from src.services.balance import BalanceCalculator


class TestBalanceCalculator(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.charlie = Member("Charlie")
        self.diana = Member("Diana")

    def test_single_equal_expense(self):
        """Alice pays $120 for 4 people equally."""
        split = EqualSplit([self.alice, self.bob, self.charlie, self.diana], Decimal("120"))
        expense = Expense("Dinner", self.alice, Decimal("120"), split)
        balances = BalanceCalculator.compute([expense])

        by_name = {b.member.name: b for b in balances}
        # Alice paid 120, owes 30 → net +90
        self.assertEqual(by_name["Alice"].net, Decimal("90.00"))
        self.assertEqual(by_name["Bob"].net, Decimal("-30.00"))
        self.assertEqual(by_name["Charlie"].net, Decimal("-30.00"))
        self.assertEqual(by_name["Diana"].net, Decimal("-30.00"))
        # Sum of all nets must be zero.
        total = sum((b.net for b in balances), Decimal("0"))
        self.assertEqual(total, Decimal("0.00"))

    def test_multiple_expenses(self):
        """Alice pays $120 equal; Bob pays $45 exact to 3 people."""
        s1 = EqualSplit([self.alice, self.bob, self.charlie, self.diana], Decimal("120"))
        e1 = Expense("Dinner", self.alice, Decimal("120"), s1)
        s2 = ExactSplit(
            [self.alice, self.bob, self.charlie],
            Decimal("45"),
            {self.alice: Decimal("15"), self.bob: Decimal("15"), self.charlie: Decimal("15")},
        )
        e2 = Expense("Taxi", self.bob, Decimal("45"), s2)

        balances = BalanceCalculator.compute([e1, e2])
        by_name = {b.member.name: b for b in balances}

        # Alice: paid 120, owes 30+15=45 → net +75
        self.assertEqual(by_name["Alice"].net, Decimal("75.00"))
        # Bob: paid 45, owes 30+15=45 → net 0
        self.assertEqual(by_name["Bob"].net, Decimal("0.00"))
        # Charlie: owes 30+15=45 → net -45
        self.assertEqual(by_name["Charlie"].net, Decimal("-45.00"))
        # Diana: owes 30 → net -30
        self.assertEqual(by_name["Diana"].net, Decimal("-30.00"))

    def test_no_expenses(self):
        balances = BalanceCalculator.compute([])
        self.assertEqual(balances, [])

    # ------------------------------------------------------------------
    # Edge Case 1: ₹100 / 3 — residue absorbed, balance is exact
    # ------------------------------------------------------------------

    def test_rupee_hundred_three_ways(self):
        """₹100.00 split equally 3 ways → shares 33.33+33.33+33.34 (last absorbs)."""
        split = EqualSplit([self.alice, self.bob, self.charlie], Decimal("100"))
        shares = split.shares()
        # Last participant (Charlie) absorbs the ₹0.01 residue.
        self.assertEqual(shares[self.alice], Decimal("33.33"))
        self.assertEqual(shares[self.bob], Decimal("33.33"))
        self.assertEqual(shares[self.charlie], Decimal("33.34"))
        self.assertEqual(sum(shares.values(), Decimal("0")), Decimal("100.00"))

        expense = Expense("Lunch", self.alice, Decimal("100"), split)
        balances = BalanceCalculator.compute([expense])
        by_name = {b.member.name: b for b in balances}
        # Alice paid 100, owes 33.33 (list position: first=get base) → net 66.67
        self.assertEqual(by_name["Alice"].net, Decimal("66.67"))
        # Bob owes 33.33 → net -33.33
        self.assertEqual(by_name["Bob"].net, Decimal("-33.33"))
        # Charlie owes 33.34 (last, absorbed residue) → net -33.34
        self.assertEqual(by_name["Charlie"].net, Decimal("-33.34"))
        # Sum of all nets must be zero.
        total = sum((b.net for b in balances), Decimal("0"))
        self.assertEqual(total, Decimal("0.00"))

    # ------------------------------------------------------------------
    # Edge Case 4: Self-payment yields net-zero
    # ------------------------------------------------------------------

    def test_self_payment(self):
        """Alice pays ₹50, sole participant Alice → net = 0."""
        split = EqualSplit([self.alice], Decimal("50"))
        expense = Expense("Self", self.alice, Decimal("50"), split)
        balances = BalanceCalculator.compute([expense])
        by_name = {b.member.name: b for b in balances}
        self.assertEqual(by_name["Alice"].paid, Decimal("50.00"))
        self.assertEqual(by_name["Alice"].owed, Decimal("50.00"))
        self.assertEqual(by_name["Alice"].net, Decimal("0.00"))

    # ------------------------------------------------------------------
    # Edge Case 5: Inactive member still appears in balance history
    # ------------------------------------------------------------------

    def test_inactive_member_in_history(self):
        """Deactivating a member doesn't erase their balance history."""
        self.charlie.deactivate()
        # Charlie is inactive but was in the split.
        split = EqualSplit([self.alice, self.bob, self.charlie], Decimal("90"))
        expense = Expense("Drinks", self.alice, Decimal("90"), split)
        balances = BalanceCalculator.compute([expense])
        by_name = {b.member.name: b for b in balances}
        # Charlie still owes ₹30 even though inactive.
        self.assertIn("Charlie", by_name)
        self.assertEqual(by_name["Charlie"].net, Decimal("-30.00"))


if __name__ == "__main__":
    unittest.main()