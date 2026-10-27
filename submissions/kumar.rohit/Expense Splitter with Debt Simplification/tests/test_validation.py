"""
Tests for input validation.
"""

import json
from decimal import Decimal

import pytest

from expense_splitter.exceptions import ValidationError
from expense_splitter.validation import validate_input


def valid_input(**overrides):
    """Minimal valid input fixture."""
    data = {
        "members": [
            {"id": "alice"},
            {"id": "bob"},
            {"id": "charlie"},
        ],
        "expenses": [
            {
                "expense_id": "e1",
                "description": "Dinner",
                "amount": 300.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob", "charlie"],
                "split_type": "equal",
            }
        ],
    }
    data.update(overrides)
    return data


class TestBasicValidation:
    """Basic valid inputs pass."""

    def test_valid_equal_split(self):
        group = validate_input(valid_input())
        assert len(group.members) == 3
        assert len(group.expenses) == 1

    def test_valid_exact_split(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob", "charlie"],
                "split_type": "exact",
                "split_details": [
                    {"member_id": "alice", "value": 200},
                    {"member_id": "bob", "value": 300},
                    {"member_id": "charlie", "value": 500},
                ],
            }]
        )
        group = validate_input(data)
        assert group.expenses[0].split_type.value == "exact"

    def test_valid_percentage_split(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob", "charlie"],
                "split_type": "percentage",
                "split_details": [
                    {"member_id": "alice", "value": 20},
                    {"member_id": "bob", "value": 30},
                    {"member_id": "charlie", "value": 50},
                ],
            }]
        )
        group = validate_input(data)
        assert group.expenses[0].split_type.value == "percentage"

    def test_payer_not_participant(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["bob", "charlie"],
                "split_type": "equal",
            }]
        )
        group = validate_input(data)
        assert group.expenses[0].payer_id == "alice"
        assert "alice" not in group.expenses[0].participant_ids

    def test_with_timestamp(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
                "timestamp": "2025-01-15T10:30:00Z",
            }]
        )
        group = validate_input(data)
        assert group.expenses[0].timestamp == "2025-01-15T10:30:00Z"

    def test_multiple_expenses(self):
        data = valid_input(
            expenses=[
                {
                    "expense_id": "e1",
                    "description": "First",
                    "amount": 300.00,
                    "currency": "INR",
                    "payer": "alice",
                    "participants": ["alice", "bob"],
                    "split_type": "equal",
                },
                {
                    "expense_id": "e2",
                    "description": "Second",
                    "amount": 500.00,
                    "currency": "INR",
                    "payer": "bob",
                    "participants": ["alice", "bob", "charlie"],
                    "split_type": "equal",
                },
            ]
        )
        group = validate_input(data)
        assert len(group.expenses) == 2

    def test_empty_expenses_list(self):
        """Empty expense list is valid (nothing to settle)."""
        data = valid_input(expenses=[])
        group = validate_input(data)
        assert len(group.expenses) == 0

    def test_optional_name_field(self):
        data = valid_input(
            members=[
                {"id": "alice", "name": "Alice Wonderland"},
                {"id": "bob"},
                {"id": "charlie"},
            ]
        )
        group = validate_input(data)
        assert group.members[0].name == "Alice Wonderland"
        assert group.members[1].name is None

    def test_member_with_name_as_string(self):
        data = {
            "members": [{"id": "alice", "name": "Alice"}],
            "expenses": [],
        }
        group = validate_input(data)
        assert group.members[0].name == "Alice"


class TestValidationErrors:
    """Rejection of invalid inputs."""

    def test_invalid_json_not_a_dict(self):
        with pytest.raises(ValidationError):
            validate_input("not an object")  # type: ignore

    def test_missing_members(self):
        with pytest.raises(ValidationError):
            validate_input({"expenses": []})

    def test_missing_expenses(self):
        with pytest.raises(ValidationError):
            validate_input({"members": [{"id": "a"}]})

    def test_members_not_list(self):
        with pytest.raises(ValidationError):
            validate_input({"members": "not_list", "expenses": []})

    def test_duplicate_member_ids(self):
        data = valid_input(
            members=[{"id": "alice"}, {"id": "alice"}]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_duplicate_expense_ids(self):
        data = valid_input(
            expenses=[
                {
                    "expense_id": "e1",
                    "description": "A",
                    "amount": 100,
                    "currency": "INR",
                    "payer": "alice",
                    "participants": ["alice", "bob"],
                    "split_type": "equal",
                },
                {
                    "expense_id": "e1",
                    "description": "B",
                    "amount": 200,
                    "currency": "INR",
                    "payer": "bob",
                    "participants": ["alice", "bob"],
                    "split_type": "equal",
                },
            ]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_unknown_payer(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "INR",
                "payer": "unknown",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "unknown" in str(exc_info.value).lower()

    def test_unknown_participant(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "unknown"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "unknown" in str(exc_info.value).lower()

    def test_empty_participant_list(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "INR",
                "payer": "alice",
                "participants": [],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "empty" in str(exc_info.value).lower() or "participants" in str(exc_info.value).lower()

    def test_exact_amounts_dont_sum(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob", "charlie"],
                "split_type": "exact",
                "split_details": [
                    {"member_id": "alice", "value": 100},
                    {"member_id": "bob", "value": 200},
                    {"member_id": "charlie", "value": 300},
                ],
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "sum" in str(exc_info.value).lower() or "does not equal" in str(exc_info.value).lower()

    def test_percentages_dont_sum_to_100(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "percentage",
                "split_details": [
                    {"member_id": "alice", "value": 30},
                    {"member_id": "bob", "value": 30},
                ],
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "100" in str(exc_info.value)

    def test_negative_exact_split(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "exact",
                "split_details": [
                    {"member_id": "alice", "value": 1100},
                    {"member_id": "bob", "value": -100},
                ],
            }]
        )
        with pytest.raises(ValidationError):
            validate_input(data)

    def test_negative_expense_total(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": -100.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "positive" in str(exc_info.value).lower()

    def test_zero_expense_total(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 0,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "positive" in str(exc_info.value).lower()

    def test_invalid_split_type(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "invalid_split",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "unsupported" in str(exc_info.value).lower()

    def test_duplicate_participants(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_duplicate_in_split_details(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000.00,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob", "charlie"],
                "split_type": "exact",
                "split_details": [
                    {"member_id": "alice", "value": 500},
                    {"member_id": "alice", "value": 500},
                ],
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_invalid_monetary_format_boolean(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": True,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "boolean" in str(exc_info.value).lower()

    def test_invalid_monetary_format_string(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": "not_a_number",
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        # "invalid decimal" or similar

    def test_excessive_decimal_precision(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100.999,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "decimal" in str(exc_info.value).lower()

    def test_infinity_amount(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": float("inf"),
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "infinity" in str(exc_info.value).lower()

    def test_nan_amount(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": float("nan"),
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "NaN" in str(exc_info.value) or "nan" in str(exc_info.value).lower()

    def test_unsupported_currency(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 100,
                "currency": "USD",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "currency" in str(exc_info.value).lower() or "USD" in str(exc_info.value)

    def test_missing_member_id(self):
        data = valid_input(
            members=[{"name": "No ID"}]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "id" in str(exc_info.value).lower()

    def test_empty_member_id(self):
        data = valid_input(
            members=[{"id": "   "}]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "empty" in str(exc_info.value).lower() or "not be empty" in str(exc_info.value).lower()

    def test_missing_expense_id(self):
        data = valid_input(
            expenses=[{
                "description": "No ID",
                "amount": 100,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "expense_id" in str(exc_info.value).lower()

    def test_negative_percentage(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "percentage",
                "split_details": [
                    {"member_id": "alice", "value": -10},
                    {"member_id": "bob", "value": 110},
                ],
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "negative" in str(exc_info.value).lower() or "percentage" in str(exc_info.value).lower()

    def test_percentage_exceeds_100(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "percentage",
                "split_details": [
                    {"member_id": "alice", "value": 120},
                    {"member_id": "bob", "value": -20},
                ],
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)

    def test_missing_split_details_for_exact(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "exact",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "split_details" in str(exc_info.value).lower()

    def test_exact_split_participant_not_in_list(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Test",
                "amount": 1000,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice", "bob"],
                "split_type": "exact",
                "split_details": [
                    {"member_id": "alice", "value": 500},
                    {"member_id": "charlie", "value": 500},
                ],
            }]
        )
        with pytest.raises(ValidationError):
            validate_input(data)

    def test_empty_members_list(self):
        data = {"members": [], "expenses": []}
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "member" in str(exc_info.value).lower()

    def test_amount_exceeds_maximum(self):
        data = valid_input(
            expenses=[{
                "expense_id": "e1",
                "description": "Huge",
                "amount": 999999999999.99,
                "currency": "INR",
                "payer": "alice",
                "participants": ["alice"],
                "split_type": "equal",
            }]
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_input(data)
        assert "maximum" in str(exc_info.value).lower()