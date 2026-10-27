"""
Tests for SettlementEngine — greedy max-heap debt simplification.
Includes Edge Cases 3 (cyclical debts, net-zero members).
"""

import unittest
from decimal import Decimal

from src.models.member import Member
from src.models.transaction import BalanceSnapshot, Transaction
from src.services.settlement import SettlementEngine


class TestSettlementEngine(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.charlie = Member("Charlie")
        self.diana = Member("Diana")
        self.eve = Member("Eve")

    def _balance(self, member, paid="0", owed="0", net="0"):
        return BalanceSnapshot(
            member=member,
            paid=Decimal(paid),
            owed=Decimal(owed),
            net=Decimal(net),
        )

    def test_simple_pair_settlement(self):
        """Alice is owed $90, Bob owes $30, Charlie owes $30, Diana owes $30."""
        balances = [
            self._balance(self.alice, "120", "30", "90"),
            self._balance(self.bob, "0", "30", "-30"),
            self._balance(self.charlie, "0", "30", "-30"),
            self._balance(self.diana, "0", "30", "-30"),
        ]
        transactions = SettlementEngine.simplify(balances)

        self.assertEqual(len(transactions), 3)
        for t in transactions:
            self.assertEqual(t.to_member, self.alice)
            self.assertEqual(t.amount, Decimal("30.00"))

    def test_no_debts(self):
        """Everyone is settled."""
        balances = [
            self._balance(self.alice, "50", "50", "0"),
            self._balance(self.bob, "50", "50", "0"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 0)

    def test_chain_settlement(self):
        """A is owed 100, B owes 100 → single transaction."""
        balances = [
            self._balance(self.alice, "100", "0", "100"),
            self._balance(self.bob, "0", "100", "-100"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].from_member, self.bob)
        self.assertEqual(transactions[0].to_member, self.alice)
        self.assertEqual(transactions[0].amount, Decimal("100.00"))

    def test_multiple_creditors_and_debtors(self):
        """A:+50, B:+30, C:-40, D:-40 — should produce minimal transactions."""
        balances = [
            self._balance(self.alice, net="50"),
            self._balance(self.bob, net="30"),
            self._balance(self.charlie, net="-40"),
            self._balance(self.diana, net="-40"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertLessEqual(len(transactions), 4)
        total_from = sum((t.amount for t in transactions), Decimal("0"))
        self.assertEqual(total_from, Decimal("80.00"))

    def test_rounding_residue_absorbed(self):
        """Tiny amounts below epsilon should be ignored."""
        balances = [
            self._balance(self.alice, net="0.004"),
            self._balance(self.bob, net="-0.004"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 0)

    def test_single_creditor_many_debtors(self):
        balances = [
            self._balance(self.alice, net="120"),
            self._balance(self.bob, net="-30"),
            self._balance(self.charlie, net="-45"),
            self._balance(self.diana, net="-45"),
        ]
        transactions = SettlementEngine.simplify(balances)
        for t in transactions:
            self.assertEqual(t.to_member, self.alice)
        total = sum((t.amount for t in transactions), Decimal("0"))
        self.assertEqual(total, Decimal("120.00"))

    def test_empty_balances(self):
        transactions = SettlementEngine.simplify([])
        self.assertEqual(transactions, [])

    def test_large_group(self):
        """50 members — stress test for O(n log n)."""
        members = [Member(f"Person_{i}") for i in range(50)]
        balances = []
        for i, m in enumerate(members):
            net = Decimal(str(100 - i * 4))
            balances.append(
                BalanceSnapshot(member=m, paid=Decimal("0"), owed=Decimal("0"), net=net)
            )
        transactions = SettlementEngine.simplify(balances)
        self.assertGreater(len(transactions), 0)

    # ------------------------------------------------------------------
    # Edge Case 3: Cyclical debts & net-zero members
    # ------------------------------------------------------------------

    def test_cyclical_debt_yields_zero_transactions(self):
        """A owes B ₹10, B owes C ₹10, C owes A ₹10 → all nets are 0.

        The algorithm should recognise this as fully settled and
        produce zero transactions.
        """
        # All three have net=0 (each owes and is owed ₹10).
        balances = [
            self._balance(self.alice, net="0"),
            self._balance(self.bob, net="0"),
            self._balance(self.charlie, net="0"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 0)

    def test_member_with_zero_net_excluded(self):
        """A member with net=0 is excluded from settlements but still present."""
        balances = [
            self._balance(self.alice, net="100"),
            self._balance(self.bob, net="0"),       # net-zero — excluded
            self._balance(self.charlie, net="-100"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 1)
        # The only transaction is Charlie → Alice.
        self.assertEqual(transactions[0].from_member, self.charlie)
        self.assertEqual(transactions[0].to_member, self.alice)

    def test_partial_cycle_with_remainder(self):
        """A:+80, B:-20, C:-20, D:-40. With a cycle: A→B→C→A (partial).

        Expected: algorithm finds the net positions and settles efficiently.
        """
        balances = [
            self._balance(self.alice, net="80"),
            self._balance(self.bob, net="-20"),
            self._balance(self.charlie, net="-20"),
            self._balance(self.diana, net="-40"),
        ]
        transactions = SettlementEngine.simplify(balances)
        # Optimal: 3 transactions (or 4, depending on matching order).
        self.assertLessEqual(len(transactions), 4)
        total = sum((t.amount for t in transactions), Decimal("0"))
        self.assertEqual(total, Decimal("80.00"))

    # ------------------------------------------------------------------
    # Edge Case 1: ₹100 / 3 residue
    # ------------------------------------------------------------------

    def test_residue_from_equal_split_through_settlement(self):
        """₹100 / 3 → nets +66.66, -33.33, -33.33 → settled correctly."""
        balances = [
            self._balance(self.alice, "100", "33.34", "66.66"),
            self._balance(self.bob, "0", "33.33", "-33.33"),
            self._balance(self.charlie, "0", "33.33", "-33.33"),
        ]
        transactions = SettlementEngine.simplify(balances)
        # Bob → Alice: 33.33, Charlie → Alice: 33.33
        self.assertEqual(len(transactions), 2)
        total = sum((t.amount for t in transactions), Decimal("0"))
        self.assertAlmostEqual(float(total), 66.66, places=2)

    # ------------------------------------------------------------------
    # Edge Case 4: Self-payment (net=0, no transactions)
    # ------------------------------------------------------------------

    def test_self_payment_yields_no_transactions(self):
        """Member pays for themselves → net=0 → excluded from settlements."""
        balances = [
            self._balance(self.alice, "50", "50", "0.00"),
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 0)

    # ------------------------------------------------------------------
    # Performance / stress: 1000 members (unlisted edge case)
    # ------------------------------------------------------------------

    def test_thousand_member_settlement(self):
        """1000 members with alternating +100/-100 balances — must complete."""
        members = [Member(f"M{i:04d}") for i in range(1000)]
        balances = [
            BalanceSnapshot(
                member=m,
                paid=Decimal("0"),
                owed=Decimal("0"),
                net=Decimal("100") if i % 2 == 0 else Decimal("-100"),
            )
            for i, m in enumerate(members)
        ]
        transactions = SettlementEngine.simplify(balances)
        # 500 creditors, 500 debtors → at least 500 transactions
        self.assertGreaterEqual(len(transactions), 500)
        # Verify total settled matches top 500 creditors.
        total = sum((t.amount for t in transactions), Decimal("0"))
        self.assertAlmostEqual(float(total), 50000.0, places=2)

    def test_all_net_zero_thousand_members(self):
        """1000 members all net-zero → 0 transactions, no crash."""
        members = [Member(f"M{i:04d}") for i in range(1000)]
        balances = [
            BalanceSnapshot(member=m, paid=Decimal("0"), owed=Decimal("0"), net=Decimal("0"))
            for m in members
        ]
        transactions = SettlementEngine.simplify(balances)
        self.assertEqual(len(transactions), 0)


if __name__ == "__main__":
    unittest.main()