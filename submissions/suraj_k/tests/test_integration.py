"""
End-to-end integration tests — from JSON file to settlement output.
Covers all five edge cases end-to-end.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.services.json_processor import JSONProcessor


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestIntegration(unittest.TestCase):

    def test_mixed_scenario_correct_settlements(self):
        """The canonical mixed scenario produces the expected settlements."""
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_mixed.json"))

        self.assertEqual(result["group"], "Team Outing 2026")
        self.assertEqual(result["member_count"], 4)
        self.assertEqual(result["expense_count"], 3)
        self.assertEqual(result["total_spent"], "565.00")

        balances = {b["member"]: b for b in result["net_balances"]}
        # Diana: paid 400, owes 270 (30 equal + 240 hotel) → net +130
        self.assertEqual(balances["Diana"]["net"], "130.00")
        # Alice: paid 120, owes 205 (30 equal + 15 taxi + 160 hotel) → net -85
        self.assertEqual(balances["Alice"]["net"], "-85.00")
        # Bob: paid 45, owes 45 (30 equal + 15 taxi) → net 0
        self.assertEqual(balances["Bob"]["net"], "0.00")
        # Charlie: paid 0, owes 45 (30 equal + 15 taxi) → net -45
        self.assertEqual(balances["Charlie"]["net"], "-45.00")

        # Settlements: Alice→Diana ₹85.00, Charlie→Diana ₹45.00
        settlements = result["settlements"]
        self.assertEqual(len(settlements), 2)
        self.assertIn(
            {"from": "Alice", "to": "Diana", "amount": "85.00"},
            settlements,
        )
        self.assertIn(
            {"from": "Charlie", "to": "Diana", "amount": "45.00"},
            settlements,
        )

    def test_equal_fixture_settlements(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_equal.json"))
        # Alice paid 120, owes 30 → net +90. Three debtors owe 30 each.
        settlements = result["settlements"]
        self.assertEqual(len(settlements), 3)
        for s in settlements:
            self.assertEqual(s["to"], "Alice")
            self.assertEqual(s["amount"], "30.00")

    def test_exact_fixture_settlements(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_exact.json"))
        # Bob paid 45, owes 15 → net +30. Alice and Charlie each owe 15.
        balances = {b["member"]: b for b in result["net_balances"]}
        self.assertEqual(balances["Bob"]["net"], "30.00")
        self.assertEqual(balances["Alice"]["net"], "-15.00")
        self.assertEqual(balances["Charlie"]["net"], "-15.00")
        settlements = result["settlements"]
        self.assertEqual(len(settlements), 2)

    def test_roundtrip_rounding_handling(self):
        """Ensure rounding doesn't accumulate errors across many expenses."""
        payload = {
            "group": {"name": "Rounding Test", "members": ["A", "B", "C"]},
            "expenses": [
                {
                    "description": f"Item {i}",
                    "payer": "A",
                    "amount": 10.00,
                    "split": {"type": "equal", "participants": ["A", "B", "C"]},
                }
                for i in range(10)
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            balances = {b["member"]: b for b in result["net_balances"]}
            # A paid 100 total, owes ~33.33 → net ~66.67.
            # Sum of all nets should be 0.
            net_sum = sum(
                float(b["net"]) for b in result["net_balances"]
            )
            self.assertAlmostEqual(net_sum, 0.0, places=2)
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Edge Case 1: ₹100 / 3 residue handling end-to-end
    # ------------------------------------------------------------------

    def test_hundred_three_ways_end_to_end(self):
        payload = {
            "group": {"name": "Hundred", "members": ["A", "B", "C"]},
            "expenses": [
                {
                    "description": "Shared meal",
                    "payer": "A",
                    "amount": 100.00,
                    "split": {"type": "equal", "participants": ["A", "B", "C"]},
                }
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            balances = {b["member"]: b for b in result["net_balances"]}
            # A paid 100, owes 33.33 → net 66.67
            self.assertEqual(balances["A"]["net"], "66.67")
            self.assertEqual(balances["B"]["net"], "-33.33")
            self.assertEqual(balances["C"]["net"], "-33.34")
            # Net sum must be zero.
            net_sum = sum(float(b["net"]) for b in result["net_balances"])
            self.assertAlmostEqual(net_sum, 0.0, places=2)
            # Settlements: B→A 33.33, C→A 33.34
            self.assertEqual(len(result["settlements"]), 2)
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Edge Case 3: Cyclical debts produce zero transactions
    # ------------------------------------------------------------------

    def test_cyclical_debts_end_to_end(self):
        """A owes B ₹10, B owes C ₹10, C owes A ₹10 → all nets zero, no settlements.
        Model: each payer is in their own split but allocates ₹0 to themselves,
        ₹10 to the beneficiary."""
        payload = {
            "group": {"name": "Cycle", "members": ["A", "B", "C"]},
            "expenses": [
                {
                    "description": "A pays for B", "payer": "A", "amount": 10.00,
                    "split": {"type": "exact", "participants": ["A", "B"],
                              "amounts": {"A": 0.00, "B": 10.00}},
                },
                {
                    "description": "B pays for C", "payer": "B", "amount": 10.00,
                    "split": {"type": "exact", "participants": ["B", "C"],
                              "amounts": {"B": 0.00, "C": 10.00}},
                },
                {
                    "description": "C pays for A", "payer": "C", "amount": 10.00,
                    "split": {"type": "exact", "participants": ["C", "A"],
                              "amounts": {"C": 0.00, "A": 10.00}},
                },
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            # All nets should be ~0 (within epsilon).
            for b in result["net_balances"]:
                self.assertAlmostEqual(float(b["net"]), 0.0, places=2)
            # No settlements needed.
            self.assertEqual(len(result["settlements"]), 0)
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Edge Case 4: Self-payment & single-member group
    # ------------------------------------------------------------------

    def test_self_payment_end_to_end(self):
        payload = {
            "group": {"name": "Solo", "members": ["Solo"]},
            "expenses": [
                {
                    "description": "My lunch", "payer": "Solo", "amount": 42.50,
                    "split": {"type": "equal", "participants": ["Solo"]},
                }
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            self.assertEqual(result["expense_count"], 1)
            balances = {b["member"]: b for b in result["net_balances"]}
            self.assertEqual(balances["Solo"]["net"], "0.00")
            self.assertEqual(len(result["settlements"]), 0)
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Edge Case 5: Inactive member (deleted mid-history)
    # ------------------------------------------------------------------

    def test_inactive_member_in_history_end_to_end(self):
        """Simulate: member existed, was deactivated, but historical debts remain."""
        # This is programmatic (JSON has no deactivate field — it's an API concern).
        from src.services.group_manager import GroupManager
        from decimal import Decimal

        gm = GroupManager("Test")
        gm.add_member("Alice")
        gm.add_member("Bob")
        gm.add_expense("Coffee", "Alice", Decimal("20"),
                       split_data={"type": "equal", "participants": ["Alice", "Bob"]})
        gm.deactivate_member("Bob")
        # Bob is inactive but still owes ₹10.
        summary = gm.summary()
        balances = {b["member"]: b for b in summary["net_balances"]}
        self.assertEqual(balances["Bob"]["net"], "-10.00")
        # Settlements should still include Bob → Alice ₹10.
        self.assertEqual(len(summary["settlements"]), 1)


if __name__ == "__main__":
    unittest.main()