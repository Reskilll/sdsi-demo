"""
Tests for validation rules (M5 + all edge cases):
  - percentages = 100, individual ≥ 0
  - exact amounts = total, individual ≥ 0
  - valid payer, payer in participants
  - positive amount, sub-paisa rejection, NaN rejection, massive-amount rejection
  - self-payment allowed, single-participant allowed
  - duplicate participants in split rejected
  - negative exact amounts rejected
  - negative percentages rejected
  - Inactive-member rejection in split
"""

import unittest
from decimal import Decimal

from src.errors import (
    MemberNotFoundError,
    SplitValidationError,
    ValidationError,
)
from src.models.expense import Expense
from src.models.member import Member
from src.models.split import (
    EqualSplit,
    ExactSplit,
    PercentageSplit,
    validate_amount,
    split_from_dict,
)


class TestAmountValidation(unittest.TestCase):
    """Edge Case 2: precision and range guards, plus NaN guard."""

    def test_positive_2dec_ok(self):
        result = validate_amount("100.50")
        self.assertEqual(result, Decimal("100.50"))

    def test_integer_ok(self):
        result = validate_amount(42)
        self.assertEqual(result, Decimal("42.00"))

    def test_sub_paisa_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_amount("100.999")
        self.assertIn("sub-paisa precision", str(ctx.exception))

    def test_negative_rejected(self):
        with self.assertRaises(ValidationError):
            validate_amount("-10.00")

    def test_zero_rejected(self):
        with self.assertRaises(ValidationError):
            validate_amount("0.00")

    def test_massive_amount_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_amount("999999999999.99")
        self.assertIn("exceeds maximum", str(ctx.exception))

    def test_junk_input_rejected(self):
        with self.assertRaises(ValidationError):
            validate_amount("not-a-number")

    def test_nan_rejected(self):
        """NaN (from JSON) must be rejected."""
        with self.assertRaises(ValidationError):
            validate_amount("NaN")

    def test_infinity_rejected(self):
        """Infinity must be rejected."""
        with self.assertRaises(ValidationError):
            validate_amount("Infinity")

    def test_negative_infinity_rejected(self):
        with self.assertRaises(ValidationError):
            validate_amount("-Infinity")


class TestValidationRules(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.charlie = Member("Charlie")

    # ------------------------------------------------------------------
    # Percentages must sum to 100
    # ------------------------------------------------------------------

    def test_percentage_sum_less_than_100_raises(self):
        with self.assertRaises(SplitValidationError) as ctx:
            PercentageSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("40"), self.bob: Decimal("50")},
            )
        self.assertIn("Percentages sum to", str(ctx.exception))

    def test_percentage_sum_more_than_100_raises(self):
        with self.assertRaises(SplitValidationError):
            PercentageSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("60"), self.bob: Decimal("50")},
            )

    def test_percentage_sum_exactly_100_succeeds(self):
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("100"),
            {self.alice: Decimal("60"), self.bob: Decimal("40")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("60.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("40.00"))

    def test_negative_percentage_rejected(self):
        """Negative percentage must be rejected (unlisted edge case)."""
        with self.assertRaises(SplitValidationError) as ctx:
            PercentageSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("110"), self.bob: Decimal("-10")},
            )
        self.assertIn("negative", str(ctx.exception))

    def test_zero_percentage_ok(self):
        """0% is valid — someone freeloads."""
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("100"),
            {self.alice: Decimal("100"), self.bob: Decimal("0")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("100.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("0.00"))

    # ------------------------------------------------------------------
    # Exact amounts must sum to total
    # ------------------------------------------------------------------

    def test_exact_sum_less_than_total_raises(self):
        with self.assertRaises(SplitValidationError) as ctx:
            ExactSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("30"), self.bob: Decimal("40")},
            )
        self.assertIn("Exact amounts sum to", str(ctx.exception))

    def test_exact_sum_more_than_total_raises(self):
        with self.assertRaises(SplitValidationError):
            ExactSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("60"), self.bob: Decimal("50")},
            )

    def test_exact_sum_matches_total_succeeds(self):
        split = ExactSplit(
            [self.alice, self.bob],
            Decimal("100"),
            {self.alice: Decimal("30"), self.bob: Decimal("70")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("30.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("70.00"))

    def test_negative_exact_amount_rejected(self):
        """Negative exact amount must be rejected (unlisted edge case)."""
        with self.assertRaises(SplitValidationError) as ctx:
            ExactSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("110"), self.bob: Decimal("-10")},
            )
        self.assertIn("negative", str(ctx.exception))

    # ------------------------------------------------------------------
    # Positive amount
    # ------------------------------------------------------------------

    def test_zero_amount_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            Expense("test", self.alice, Decimal("0"))
        self.assertIn("must be positive", str(ctx.exception))

    def test_negative_amount_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            Expense("test", self.alice, Decimal("-50"))
        self.assertIn("must be positive", str(ctx.exception))

    # ------------------------------------------------------------------
    # Participant minimum (Edge Case 4)
    # ------------------------------------------------------------------

    def test_no_participants_raises(self):
        with self.assertRaises(SplitValidationError):
            EqualSplit([], Decimal("100"))

    def test_single_participant_allowed(self):
        split = EqualSplit([self.alice], Decimal("50"))
        self.assertEqual(split.share_for(self.alice), Decimal("50.00"))

    # ------------------------------------------------------------------
    # Duplicate participants in split (unlisted edge case)
    # ------------------------------------------------------------------

    def test_duplicate_participant_in_split_raises(self):
        with self.assertRaises(SplitValidationError) as ctx:
            EqualSplit([self.alice, self.bob, self.alice], Decimal("100"))
        self.assertIn("Duplicate participant", str(ctx.exception))

    def test_duplicate_participant_name_in_dict(self):
        """JSON with duplicate names in participants list must be rejected."""
        member_map = {"Alice": self.alice, "Bob": self.bob}
        with self.assertRaises(SplitValidationError) as ctx:
            split_from_dict(
                {"type": "equal", "participants": ["Alice", "Bob", "Alice"]},
                member_map,
                Decimal("100"),
            )
        self.assertIn("Duplicate", str(ctx.exception))

    # ------------------------------------------------------------------
    # Payer must be in participants
    # ------------------------------------------------------------------

    def test_payer_not_in_participants_raises(self):
        eve = Member("Eve")
        split = EqualSplit([self.alice, self.bob], Decimal("100"))
        with self.assertRaises(MemberNotFoundError) as ctx:
            Expense("test", eve, Decimal("100"), split)
        self.assertIn("must be among the split participants", str(ctx.exception))

    def test_payer_in_participants_succeeds(self):
        split = EqualSplit([self.alice, self.bob], Decimal("100"))
        expense = Expense("test", self.alice, Decimal("100"), split)
        self.assertEqual(expense.payer, self.alice)

    # ------------------------------------------------------------------
    # Edge Case 4: Self-payment
    # ------------------------------------------------------------------

    def test_self_payment_legal(self):
        split = EqualSplit([self.alice], Decimal("50"))
        expense = Expense("Self-paid item", self.alice, Decimal("50"), split)
        self.assertEqual(expense.total_amount, Decimal("50.00"))
        self.assertEqual(expense.split.share_for(self.alice), Decimal("50.00"))


if __name__ == "__main__":
    unittest.main()