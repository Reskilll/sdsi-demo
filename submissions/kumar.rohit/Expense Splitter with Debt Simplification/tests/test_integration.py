"""
Integration tests: engine pipeline, JSON I/O, CLI, and full scenarios.
"""

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from expense_splitter.engine import process_group
from expense_splitter.exceptions import ValidationError
from expense_splitter.io import format_human_readable, format_json_output, read_expenses, result_to_dict
from expense_splitter.models import Expense, ExpenseGroup, Member, SplitEntry, SplitType
from expense_splitter.validation import validate_input


def write_temp_json(data: dict) -> Path:
    tmp = NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


class TestEnginePipeline:
    """End-to-end pipeline tests."""

    def test_full_pipeline_equal_split(self):
        group = ExpenseGroup(
            members=(Member(id="a"), Member(id="b"), Member(id="c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Dinner",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        result = process_group(group)
        assert result.expense_count == 1
        assert result.member_count == 3
        assert len(result.balances) == 3
        # Only need settlements for non-zero members
        for s in result.settlements:
            assert s.amount > 0
            assert s.from_member_id != s.to_member_id

    def test_full_pipeline_empty_expenses(self):
        group = ExpenseGroup(
            members=(Member(id="a"), Member(id="b")),
            expenses=(),
        )
        result = process_group(group)
        assert result.expense_count == 0
        for b in result.balances:
            assert b.net_balance == Decimal("0")
        assert len(result.settlements) == 0

    def test_full_pipeline_complex_scenario(self):
        """Multi-expense, multi-payer, mixed split types."""
        group = ExpenseGroup(
            members=(
                Member(id="alice"), Member(id="bob"), Member(id="charlie"),
                Member(id="diana"), Member(id="eve"),
            ),
            expenses=(
                # Dinner: Alice pays 1000, equal split for alice, bob, charlie
                Expense(
                    expense_id="e1",
                    description="Dinner",
                    amount=Decimal("1000.00"),
                    currency="INR",
                    payer_id="alice",
                    participant_ids=("alice", "bob", "charlie"),
                    split_type=SplitType.EQUAL,
                ),
                # Movie: Bob pays 600, exact split
                Expense(
                    expense_id="e2",
                    description="Movie",
                    amount=Decimal("600.00"),
                    currency="INR",
                    payer_id="bob",
                    participant_ids=("alice", "bob", "diana"),
                    split_type=SplitType.EXACT,
                    split_details=(
                        SplitEntry("alice", Decimal("150")),
                        SplitEntry("bob", Decimal("200")),
                        SplitEntry("diana", Decimal("250")),
                    ),
                ),
                # Groceries: Charlie pays 800, percentage split
                Expense(
                    expense_id="e3",
                    description="Groceries",
                    amount=Decimal("800.00"),
                    currency="INR",
                    payer_id="charlie",
                    participant_ids=("alice", "bob", "charlie", "diana"),
                    split_type=SplitType.PERCENTAGE,
                    split_details=(
                        SplitEntry("alice", Decimal("20")),
                        SplitEntry("bob", Decimal("30")),
                        SplitEntry("charlie", Decimal("50")),
                        SplitEntry("diana", Decimal("0")),
                    ),
                ),
            ),
        )
        result = process_group(group)

        # Verify invariants
        by_id = {b.member_id: b for b in result.balances}
        assert "eve" in by_id
        assert by_id["eve"].net_balance == Decimal("0")

        # Sum of balances = 0
        total = sum(b.net_balance for b in result.balances)
        assert total == Decimal("0")

        # Settlements resolve balances
        final = {b.member_id: b.net_balance for b in result.balances}
        for s in result.settlements:
            final[s.from_member_id] += s.amount
            final[s.to_member_id] -= s.amount
        for mid, bal in final.items():
            assert bal == Decimal("0"), f"{mid}: {bal}"


class TestJSONInput:
    """Read and validate expenses from JSON files."""

    def test_read_valid_json(self):
        data = {
            "members": [{"id": "alice"}, {"id": "bob"}],
            "expenses": [
                {
                    "expense_id": "e1",
                    "description": "Lunch",
                    "amount": 200.00,
                    "currency": "INR",
                    "payer": "alice",
                    "participants": ["alice", "bob"],
                    "split_type": "equal",
                }
            ],
        }
        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            assert len(group.members) == 2
            assert len(group.expenses) == 1
        finally:
            os.unlink(path)

    def test_read_invalid_json(self):
        path = write_temp_json({"not": "valid"})
        # Remove members field
        try:
            with pytest.raises(ValidationError):
                read_expenses(path)
        finally:
            os.unlink(path)

    def test_read_malformed_json(self):
        path = Path(NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8").name)
        path.write_text("{invalid json")
        try:
            with pytest.raises(ValidationError):
                read_expenses(path)
        finally:
            os.unlink(path)

    def test_read_nonexistent_file(self):
        with pytest.raises(ValidationError):
            read_expenses("/nonexistent/file.json")

    def test_read_empty_file(self):
        path = Path(NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8").name)
        path.write_text("")
        try:
            with pytest.raises(ValidationError):
                read_expenses(path)
        finally:
            os.unlink(path)


class TestJSONOutput:
    """Output formatting tests."""

    def test_json_output_valid(self):
        from expense_splitter.engine import process_group
        from expense_splitter.models import Expense, ExpenseGroup, Member, SplitType

        group = ExpenseGroup(
            members=(Member(id="a"), Member(id="b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        result = process_group(group)
        d = result_to_dict(result)
        assert "balances" in d
        assert "settlements" in d
        assert "summary" in d
        # All amounts should be strings (for safe JSON)
        for b in d["balances"]:
            assert isinstance(b["net_balance"], str)
        for s in d["settlements"]:
            assert isinstance(s["amount"], str)

    def test_json_output_parsable(self):
        from expense_splitter.engine import process_group
        from expense_splitter.models import Expense, ExpenseGroup, Member, SplitType

        group = ExpenseGroup(
            members=(Member(id="a"), Member(id="b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        result = process_group(group)
        output = format_json_output(result)
        parsed = json.loads(output)
        assert parsed["summary"]["expense_count"] == 1

    def test_human_readable_output(self):
        from expense_splitter.engine import process_group
        from expense_splitter.models import Expense, ExpenseGroup, Member, SplitType

        group = ExpenseGroup(
            members=(Member(id="alice"), Member(id="bob")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Dinner",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="alice",
                    participant_ids=("alice", "bob"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        result = process_group(group)
        output = format_human_readable(result)
        assert "alice" in output
        assert "bob" in output
        assert "₹" in output


class TestEndToEndScenarios:
    """Complete scenarios similar to the README examples."""

    def test_sample_from_readme(self):
        """The scenario described in the problem statement."""
        data = {
            "members": [
                {"id": "alice"},
                {"id": "bob"},
                {"id": "charlie"},
                {"id": "diana"},
                {"id": "eve"},
            ],
            "expenses": [
                {
                    "expense_id": "exp1",
                    "description": "Dinner at Taj",
                    "amount": 1000.00,
                    "currency": "INR",
                    "payer": "alice",
                    "participants": ["alice", "bob", "charlie"],
                    "split_type": "equal",
                },
                {
                    "expense_id": "exp2",
                    "description": "Movie tickets",
                    "amount": 600.00,
                    "currency": "INR",
                    "payer": "bob",
                    "participants": ["alice", "bob", "diana"],
                    "split_type": "exact",
                    "split_details": [
                        {"member_id": "alice", "value": 150.00},
                        {"member_id": "bob", "value": 200.00},
                        {"member_id": "diana", "value": 250.00},
                    ],
                },
                {
                    "expense_id": "exp3",
                    "description": "Groceries",
                    "amount": 800.00,
                    "currency": "INR",
                    "payer": "charlie",
                    "participants": ["alice", "bob", "charlie", "diana"],
                    "split_type": "percentage",
                    "split_details": [
                        {"member_id": "alice", "value": 20},
                        {"member_id": "bob", "value": 30},
                        {"member_id": "charlie", "value": 50},
                        {"member_id": "diana", "value": 0},
                    ],
                },
                {
                    "expense_id": "exp4",
                    "description": "Cab ride",
                    "amount": 300.00,
                    "currency": "INR",
                    "payer": "diana",
                    "participants": ["alice", "charlie"],
                    "split_type": "equal",
                },
                {
                    "expense_id": "exp5",
                    "description": "Diana pays for Eve's lunch",
                    "amount": 450.50,
                    "currency": "INR",
                    "payer": "diana",
                    "participants": ["eve"],
                    "split_type": "equal",
                },
            ],
        }

        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            result = process_group(group)

            # Sum of balances = 0
            total = sum(b.net_balance for b in result.balances)
            assert total == Decimal("0")

            # Verify settlements resolve
            final = {b.member_id: b.net_balance for b in result.balances}
            for s in result.settlements:
                final[s.from_member_id] += s.amount
                final[s.to_member_id] -= s.amount
            for mid, bal in final.items():
                assert bal == Decimal("0"), f"{mid} not settled: {bal}"

            # No self-transfers
            for s in result.settlements:
                assert s.from_member_id != s.to_member_id
                assert s.amount > 0

        finally:
            os.unlink(path)

    def test_batch_processing(self):
        """Process multiple expenses from JSON."""
        data = {
            "members": [{"id": f"m{i}"} for i in range(5)],
            "expenses": [
                {
                    "expense_id": f"e{i}",
                    "description": f"Expense {i}",
                    "amount": 100.00 * (i + 1),
                    "currency": "INR",
                    "payer": f"m{i % 5}",
                    "participants": [f"m{j}" for j in range(5)],
                    "split_type": "equal",
                }
                for i in range(10)
            ],
        }
        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            result = process_group(group)
            assert result.expense_count == 10
            assert result.member_count == 5
            total = sum(b.net_balance for b in result.balances)
            assert total == Decimal("0")
        finally:
            os.unlink(path)

    def test_single_member_group(self):
        """Single-member group: payer = participant."""
        data = {
            "members": [{"id": "solo"}],
            "expenses": [
                {
                    "expense_id": "e1",
                    "description": "Solo expense",
                    "amount": 500.00,
                    "currency": "INR",
                    "payer": "solo",
                    "participants": ["solo"],
                    "split_type": "equal",
                },
            ],
        }
        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            result = process_group(group)
            # Solo person paid 500 and owes 500 → net 0
            assert result.balances[0].net_balance == Decimal("0")
            assert len(result.settlements) == 0
        finally:
            os.unlink(path)

    def test_member_paid_but_no_participation(self):
        """Member paid for others but didn't participate in any expense."""
        data = {
            "members": [{"id": "generous"}, {"id": "b"}],
            "expenses": [
                {
                    "expense_id": "e1",
                    "description": "Gift",
                    "amount": 200.00,
                    "currency": "INR",
                    "payer": "generous",
                    "participants": ["b"],
                    "split_type": "equal",
                },
            ],
        }
        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            result = process_group(group)
            by_id = {b.member_id: b for b in result.balances}
            assert by_id["generous"].net_balance == Decimal("200.00")
            assert by_id["b"].net_balance == Decimal("-200.00")
        finally:
            os.unlink(path)

    def test_exact_cancellation(self):
        """Multiple expenses producing exact cancellation."""
        data = {
            "members": [{"id": "a"}, {"id": "b"}],
            "expenses": [
                {
                    "expense_id": "e1",
                    "description": "A pays",
                    "amount": 100.00,
                    "currency": "INR",
                    "payer": "a",
                    "participants": ["a", "b"],
                    "split_type": "equal",
                },
                {
                    "expense_id": "e2",
                    "description": "B pays",
                    "amount": 100.00,
                    "currency": "INR",
                    "payer": "b",
                    "participants": ["a", "b"],
                    "split_type": "equal",
                },
            ],
        }
        path = write_temp_json(data)
        try:
            group = read_expenses(path)
            result = process_group(group)
            for b in result.balances:
                assert b.net_balance == Decimal("0")
            assert len(result.settlements) == 0
        finally:
            os.unlink(path)


class TestCLI:
    """CLI entry point tests (functional, no subprocess)."""

    def test_cli_help(self):
        from expense_splitter.__main__ import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_cli_missing_input(self):
        from expense_splitter.__main__ import main
        # --input is optional now (for --serve mode); missing input returns exit code 1
        exit_code = main([])
        assert exit_code == 1

    def test_cli_valid_file(self):
        data = {
            "members": [{"id": "a"}, {"id": "b"}],
            "expenses": [
                {
                    "expense_id": "e1",
                    "description": "Test",
                    "amount": 100.00,
                    "currency": "INR",
                    "payer": "a",
                    "participants": ["a", "b"],
                    "split_type": "equal",
                }
            ],
        }
        path = write_temp_json(data)
        try:
            from expense_splitter.__main__ import main
            exit_code = main(["--input", str(path)])
            assert exit_code == 0
        finally:
            os.unlink(path)

    def test_cli_json_mode(self):
        data = {
            "members": [{"id": "a"}, {"id": "b"}],
            "expenses": [],
        }
        path = write_temp_json(data)
        try:
            from expense_splitter.__main__ import main
            exit_code = main(["--input", str(path), "--json"])
            assert exit_code == 0
        finally:
            os.unlink(path)

    def test_cli_invalid_file(self):
        from expense_splitter.__main__ import main
        exit_code = main(["--input", "/nonexistent.json"])
        assert exit_code == 1