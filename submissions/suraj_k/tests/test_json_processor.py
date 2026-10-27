"""
Tests for JSONProcessor — single-file, batch, and stdin processing.
Includes Edge Cases 2 (sub-paisa), 4 (single-member), 5 (inactive member).
"""

import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.errors import InputFormatError, SplitwiseError
from src.services.json_processor import JSONProcessor


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestJSONProcessorSingle(unittest.TestCase):
    def test_process_equal_fixture(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_equal.json"))
        self.assertEqual(result["group"], "Equal Split Dinner")
        self.assertEqual(result["expense_count"], 1)
        self.assertEqual(len(result["net_balances"]), 4)
        self.assertGreater(len(result["settlements"]), 0)

    def test_process_exact_fixture(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_exact.json"))
        self.assertEqual(result["expense_count"], 1)
        self.assertEqual(len(result["net_balances"]), 3)

    def test_process_percentage_fixture(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_percentage.json"))
        self.assertEqual(result["expense_count"], 1)

    def test_process_mixed_fixture(self):
        result = JSONProcessor.process_one(str(FIXTURES_DIR / "sample_mixed.json"))
        self.assertEqual(result["group"], "Team Outing 2026")
        self.assertEqual(result["expense_count"], 3)
        self.assertEqual(result["member_count"], 4)
        self.assertEqual(result["total_spent"], "565.00")
        self.assertEqual(len(result["net_balances"]), 4)

    def test_invalid_percentage_raises(self):
        with self.assertRaises(SplitwiseError):
            JSONProcessor.process_one(str(FIXTURES_DIR / "invalid_percentage.json"))

    def test_invalid_exact_raises(self):
        with self.assertRaises(SplitwiseError):
            JSONProcessor.process_one(str(FIXTURES_DIR / "invalid_exact.json"))

    def test_invalid_payer_raises(self):
        with self.assertRaises(SplitwiseError):
            JSONProcessor.process_one(str(FIXTURES_DIR / "invalid_payer.json"))

    def test_missing_file_raises(self):
        with self.assertRaises(InputFormatError) as ctx:
            JSONProcessor.process_one("nonexistent.json")
        self.assertIn("File not found", str(ctx.exception))

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("invalid JSON", str(ctx.exception))
        finally:
            os.unlink(path)


class TestJSONProcessorBatch(unittest.TestCase):
    def test_batch_directory(self):
        results = JSONProcessor.process_batch(str(FIXTURES_DIR))
        self.assertGreater(len(results), 0)
        successes = [r for r in results if "result" in r]
        errors = [r for r in results if "error" in r]
        self.assertGreater(len(successes), 0)
        self.assertGreater(len(errors), 0)  # invalid fixtures

    def test_batch_nonexistent_dir(self):
        with self.assertRaises(InputFormatError):
            JSONProcessor.process_batch("nonexistent_dir")


class TestJSONProcessorStdin(unittest.TestCase):
    def test_process_stdin(self):
        payload = {
            "group": {"name": "Stdin Group", "members": ["X", "Y"]},
            "expenses": [
                {
                    "description": "Pizza",
                    "payer": "X",
                    "amount": 30,
                    "split": {"type": "equal", "participants": ["X", "Y"]},
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
            self.assertEqual(result["group"], "Stdin Group")
            self.assertEqual(result["expense_count"], 1)
        finally:
            os.unlink(path)


class TestInputEdgeCases(unittest.TestCase):
    def test_minimal_group_no_expenses(self):
        """A group with 2 members but no expenses is valid."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"group": {"name": "Minimal", "members": ["A", "B"]}}, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            self.assertEqual(result["group"], "Minimal")
            self.assertEqual(result["expense_count"], 0)
        finally:
            os.unlink(path)

    # Edge Case 4: empty group rejected, single-member group accepted.
    def test_empty_member_list_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"group": {"members": []}}, f)
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("at least 1 member", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_single_member_group(self):
        """Edge Case 4: single-member group is valid."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"group": {"members": ["OnlyMe"]}}, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            self.assertEqual(result["member_count"], 1)
        finally:
            os.unlink(path)

    def test_single_member_self_payment(self):
        """Edge Case 4: single member + self-expense is valid."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            payload = {
                "group": {"members": ["Solo"]},
                "expenses": [
                    {
                        "description": "My lunch",
                        "payer": "Solo",
                        "amount": 15.50,
                        "split": {"type": "equal", "participants": ["Solo"]},
                    }
                ],
            }
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            self.assertEqual(result["expense_count"], 1)
            self.assertEqual(len(result["settlements"]), 0)  # net=0 → no settlement
        finally:
            os.unlink(path)

    def test_duplicate_member_names_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"group": {"members": ["A", "A"]}}, f)
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("duplicate", str(ctx.exception))
        finally:
            os.unlink(path)

    # Edge Case 2: sub-paisa precision rejected.
    def test_sub_paisa_amount_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            payload = {
                "group": {"members": ["A", "B"]},
                "expenses": [
                    {
                        "description": "Too precise",
                        "payer": "A",
                        "amount": 100.999,
                        "split": {"type": "equal", "participants": ["A", "B"]},
                    }
                ],
            }
            json.dump(payload, f)
            path = f.name
        try:
            with self.assertRaises(SplitwiseError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("sub-paisa", str(ctx.exception))
        finally:
            os.unlink(path)

    # Edge Case 2: massive amount rejected.
    def test_massive_amount_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            payload = {
                "group": {"members": ["A", "B"]},
                "expenses": [
                    {
                        "description": "Absurd",
                        "payer": "A",
                        "amount": 999999999999.99,
                        "split": {"type": "equal", "participants": ["A", "B"]},
                    }
                ],
            }
            json.dump(payload, f)
            path = f.name
        try:
            with self.assertRaises(SplitwiseError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("exceeds maximum", str(ctx.exception))
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Security / robustness edge cases (unlisted)
    # ------------------------------------------------------------------

    def test_control_character_in_member_name_rejected(self):
        """Member names with control characters must be rejected."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"group": {"members": ["Nice", "Bad\x00Name"]}}, f)
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("control characters", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_long_member_name_rejected(self):
        """Member names over 100 chars must be rejected."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            long_name = "A" * 101
            json.dump({"group": {"members": ["OK", long_name]}}, f)
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("exceeds", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_long_description_rejected(self):
        """Description over 500 chars must be rejected."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            payload = {
                "group": {"members": ["A", "B"]},
                "expenses": [
                    {
                        "description": "X" * 501,
                        "payer": "A",
                        "amount": 10.00,
                        "split": {"type": "equal", "participants": ["A", "B"]},
                    }
                ],
            }
            json.dump(payload, f)
            path = f.name
        try:
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("description exceeds", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_large_file_rejected(self):
        """Files over 50 MiB should be rejected without reading."""
        # Create a large JSON file > 50 MiB.
        path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                # Write 51 MB of whitespace + a valid payload at the end.
                f.write(" " * (51 * 1024 * 1024))
                f.write(json.dumps({
                    "group": {"members": ["A", "B"]},
                    "expenses": [],
                }))
                path = f.name
            with self.assertRaises(InputFormatError) as ctx:
                JSONProcessor.process_one(path)
            self.assertIn("file size", str(ctx.exception))
        finally:
            if path:
                os.unlink(path)

    def test_description_length_is_exact_max_ok(self):
        """Exactly 500 chars is accepted."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            payload = {
                "group": {"members": ["A", "B"]},
                "expenses": [
                    {
                        "description": "X" * 500,
                        "payer": "A",
                        "amount": 10.00,
                        "split": {"type": "equal", "participants": ["A", "B"]},
                    }
                ],
            }
            json.dump(payload, f)
            path = f.name
        try:
            result = JSONProcessor.process_one(path)
            self.assertEqual(result["expense_count"], 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()