"""
Tests for GroupManager — including soft-delete lifecycle (Edge Case 5)
and self-payment (Edge Case 4).
"""

import unittest
from decimal import Decimal

from src.errors import InactiveMemberError, MemberNotFoundError
from src.models.member import Member
from src.services.group_manager import GroupManager


class TestGroupManager(unittest.TestCase):
    def setUp(self):
        self.gm = GroupManager("Test Group")

    def test_add_member(self):
        m = self.gm.add_member("Alice")
        self.assertEqual(m.name, "Alice")
        self.assertEqual(self.gm.member_count, 1)
        self.assertEqual(self.gm.active_member_count, 1)

    def test_duplicate_member_raises(self):
        self.gm.add_member("Alice")
        with self.assertRaises(MemberNotFoundError) as ctx:
            self.gm.add_member("Alice")
        self.assertIn("already exists", str(ctx.exception))

    def test_add_expense_equal_split(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.add_member("Charlie")
        expense = self.gm.add_expense(
            "Lunch",
            payer_name="Alice",
            amount=Decimal("90"),
            split_data={
                "type": "equal",
                "participants": ["Alice", "Bob", "Charlie"],
            },
        )
        self.assertEqual(expense.total_amount, Decimal("90"))
        self.assertEqual(self.gm.expense_count, 1)

    def test_add_expense_invalid_payer(self):
        self.gm.add_member("Alice")
        with self.assertRaises(MemberNotFoundError) as ctx:
            self.gm.add_expense(
                "Lunch", payer_name="Bob", amount=Decimal("50"),
                split_data={"type": "equal", "participants": ["Alice"]},
            )
        self.assertIn("not a member of the group", str(ctx.exception))

    def test_net_balances_after_one_expense(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.add_expense(
            "Coffee", "Alice", Decimal("20"),
            split_data={
                "type": "equal",
                "participants": ["Alice", "Bob"],
            },
        )
        balances = self.gm.net_balances()
        by_name = {b.member.name: b for b in balances}
        self.assertEqual(by_name["Alice"].net, Decimal("10.00"))
        self.assertEqual(by_name["Bob"].net, Decimal("-10.00"))

    def test_simplify_debts(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.add_expense(
            "Coffee", "Alice", Decimal("20"),
            split_data={
                "type": "equal",
                "participants": ["Alice", "Bob"],
            },
        )
        transactions = self.gm.simplify_debts()
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].from_member.name, "Bob")
        self.assertEqual(transactions[0].to_member.name, "Alice")
        self.assertEqual(transactions[0].amount, Decimal("10.00"))

    def test_summary_output(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.add_expense("Coffee", "Alice", Decimal("20"),
                            split_data={"type": "equal", "participants": ["Alice", "Bob"]})
        summary = self.gm.summary()
        self.assertEqual(summary["group"], "Test Group")
        self.assertEqual(summary["member_count"], 2)
        self.assertEqual(summary["expense_count"], 1)
        self.assertIn("net_balances", summary)
        self.assertIn("settlements", summary)

    def test_get_member_by_name_missing_raises(self):
        with self.assertRaises(MemberNotFoundError):
            self.gm.get_member_by_name("Nobody")

    # ------------------------------------------------------------------
    # Edge Case 5: Soft-delete lifecycle
    # ------------------------------------------------------------------

    def test_deactivate_member(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.deactivate_member("Bob")
        self.assertFalse(self.gm.get_member_by_name("Bob").is_active)
        self.assertEqual(self.gm.active_member_count, 1)

    def test_deactivate_nonexistent_raises(self):
        with self.assertRaises(MemberNotFoundError):
            self.gm.deactivate_member("Nobody")

    def test_double_deactivate_raises(self):
        self.gm.add_member("Alice")
        self.gm.deactivate_member("Alice")
        with self.assertRaises(InactiveMemberError):
            self.gm.deactivate_member("Alice")

    def test_reactivate_member(self):
        self.gm.add_member("Alice")
        self.gm.deactivate_member("Alice")
        self.gm.reactivate_member("Alice")
        self.assertTrue(self.gm.get_member_by_name("Alice").is_active)

    def test_inactive_payer_cannot_create_expense(self):
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.deactivate_member("Alice")
        with self.assertRaises(InactiveMemberError) as ctx:
            self.gm.add_expense(
                "Should fail", "Alice", Decimal("50"),
                split_data={"type": "equal", "participants": ["Alice", "Bob"]},
            )
        self.assertIn("deactivated", str(ctx.exception))

    def test_inactive_member_in_history_still_appears_in_balances(self):
        """Deactivated members with historical balances still show up."""
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.add_expense("Coffee", "Alice", Decimal("20"),
                            split_data={"type": "equal", "participants": ["Alice", "Bob"]})
        self.gm.deactivate_member("Bob")
        balances = self.gm.net_balances()
        by_name = {b.member.name: b for b in balances}
        # Bob still owes ₹10 even though he's inactive.
        self.assertEqual(by_name["Bob"].net, Decimal("-10.00"))
        # Total member_count still counts Bob.
        self.assertEqual(self.gm.member_count, 2)
        self.assertEqual(self.gm.active_member_count, 1)

    def test_default_split_excludes_inactive(self):
        """When split_data is None, default should use only active members."""
        self.gm.add_member("Alice")
        self.gm.add_member("Bob")
        self.gm.deactivate_member("Bob")
        # Default split uses only active members → just Alice.
        # With 1 active participant, this is a self-payment (Edge Case 4).
        expense = self.gm.add_expense("Lunch", "Alice", Decimal("30"))
        self.assertEqual(len(expense.split.participants), 1)
        self.assertEqual(expense.split.participants[0].name, "Alice")
        # Self-payment → net zero, no settlements.

    # ------------------------------------------------------------------
    # Edge Case 4: Self-payment
    # ------------------------------------------------------------------

    def test_self_payment_through_group_manager(self):
        """Self-payment produces net-zero balance."""
        self.gm.add_member("Alice")
        self.gm.add_expense("Personal item", "Alice", Decimal("100"),
                            split_data={"type": "equal", "participants": ["Alice"]})
        balances = self.gm.net_balances()
        by_name = {b.member.name: b for b in balances}
        self.assertEqual(by_name["Alice"].net, Decimal("0.00"))
        # No settlements needed.
        self.assertEqual(len(self.gm.simplify_debts()), 0)

    def test_single_member_group(self):
        """Edge Case 4: group with one member is valid."""
        self.gm.add_member("OnlyMe")
        self.assertEqual(self.gm.member_count, 1)
        self.assertEqual(self.gm.summary()["member_count"], 1)


if __name__ == "__main__":
    unittest.main()