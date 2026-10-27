"""
Tests for split computation correctness — Equal, Exact, Percentage.
Covers unified cached-shares mechanism, residue absorption, self-payment,
and inactive-member rejection.
"""

import unittest
from decimal import Decimal

from src.errors import SplitValidationError
from src.models.member import Member
from src.models.split import EqualSplit, ExactSplit, PercentageSplit, split_from_dict


class TestEqualSplit(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.charlie = Member("Charlie")
        self.diana = Member("Diana")

    def test_evenly_divisible(self):
        split = EqualSplit([self.alice, self.bob, self.charlie, self.diana], Decimal("120.00"))
        self.assertEqual(split.share_for(self.alice), Decimal("30.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("30.00"))

    def test_rounding_residue_absorbed_by_last(self):
        """₹100 / 3 = 33.33 each, residue on *last* participant."""
        split = EqualSplit([self.alice, self.bob, self.charlie], Decimal("100"))
        shares = split.shares()
        # First two get 33.33, last absorbs residue → 33.34.
        self.assertEqual(shares[self.alice], Decimal("33.33"))
        self.assertEqual(shares[self.bob], Decimal("33.33"))
        self.assertEqual(shares[self.charlie], Decimal("33.34"))
        total = sum(shares.values(), Decimal("0"))
        self.assertEqual(total, Decimal("100.00"))

    def test_share_for_matches_shares(self):
        """share_for() and shares() must agree — cached-shares guarantee."""
        split = EqualSplit([self.alice, self.bob, self.charlie], Decimal("100"))
        single = split.share_for(self.alice)
        bulk = split.shares()
        self.assertEqual(single, bulk[self.alice])

    def test_non_participant_gets_zero(self):
        eve = Member("Eve")
        split = EqualSplit([self.alice, self.bob], Decimal("100"))
        self.assertEqual(split.share_for(eve), Decimal("0.00"))

    def test_two_participants(self):
        split = EqualSplit([self.alice, self.bob], Decimal("50"))
        shares = split.shares()
        self.assertEqual(shares[self.alice], Decimal("25.00"))
        self.assertEqual(shares[self.bob], Decimal("25.00"))

    # Edge Case 4: single-participant self-payment.
    def test_single_participant_self_payment(self):
        """A pays for A — legal self-payment, net = 0."""
        split = EqualSplit([self.alice], Decimal("42.00"))
        shares = split.shares()
        self.assertEqual(shares[self.alice], Decimal("42.00"))
        self.assertEqual(split.share_for(self.alice), Decimal("42.00"))


class TestExactSplit(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.charlie = Member("Charlie")

    def test_basic(self):
        split = ExactSplit(
            [self.alice, self.bob, self.charlie],
            Decimal("45"),
            {self.alice: Decimal("15"), self.bob: Decimal("15"), self.charlie: Decimal("15")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("15.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("15.00"))

    def test_unequal_amounts(self):
        split = ExactSplit(
            [self.alice, self.bob],
            Decimal("100"),
            {self.alice: Decimal("75.50"), self.bob: Decimal("24.50")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("75.50"))
        self.assertEqual(split.share_for(self.bob), Decimal("24.50"))

    def test_non_participant_gets_zero(self):
        eve = Member("Eve")
        split = ExactSplit(
            [self.alice, self.bob],
            Decimal("50"),
            {self.alice: Decimal("25"), self.bob: Decimal("25")},
        )
        self.assertEqual(split.share_for(eve), Decimal("0.00"))

    def test_sum_must_equal_total(self):
        with self.assertRaises(SplitValidationError):
            ExactSplit(
                [self.alice, self.bob],
                Decimal("100"),
                {self.alice: Decimal("30"), self.bob: Decimal("69")},
            )

    # Edge Case 4: single-participant exact split.
    def test_single_participant_exact(self):
        split = ExactSplit(
            [self.alice], Decimal("99.99"),
            {self.alice: Decimal("99.99")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("99.99"))


class TestPercentageSplit(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")

    def test_basic(self):
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("400"),
            {self.alice: Decimal("40"), self.bob: Decimal("60")},
        )
        self.assertEqual(split.share_for(self.alice), Decimal("160.00"))
        self.assertEqual(split.share_for(self.bob), Decimal("240.00"))

    def test_non_participant_gets_zero(self):
        eve = Member("Eve")
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("200"),
            {self.alice: Decimal("50"), self.bob: Decimal("50")},
        )
        self.assertEqual(split.share_for(eve), Decimal("0.00"))

    def test_percentage_residue_absorbed_by_last(self):
        """When percentages produce rounding residue, last participant absorbs it."""
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("100"),
            {self.alice: Decimal("33.33"), self.bob: Decimal("66.67")},
        )
        total = split.share_for(self.alice) + split.share_for(self.bob)
        self.assertEqual(total, Decimal("100.00"))

    def test_share_for_matches_shares(self):
        split = PercentageSplit(
            [self.alice, self.bob],
            Decimal("199.99"),
            {self.alice: Decimal("33.33"), self.bob: Decimal("66.67")},
        )
        single = split.share_for(self.alice)
        bulk = split.shares()
        self.assertEqual(single, bulk[self.alice])


class TestSplitFromDict(unittest.TestCase):
    def setUp(self):
        self.alice = Member("Alice")
        self.bob = Member("Bob")
        self.member_map = {"Alice": self.alice, "Bob": self.bob}

    def test_equal_split_from_dict(self):
        d = {"type": "equal", "participants": ["Alice", "Bob"]}
        split = split_from_dict(d, self.member_map, Decimal("100"), [self.alice, self.bob])
        self.assertIsInstance(split, EqualSplit)

    def test_inactive_member_rejected(self):
        """Edge Case 5: inactive member cannot be in new split."""
        self.bob.deactivate()
        d = {"type": "equal", "participants": ["Alice", "Bob"]}
        from src.errors import MemberNotFoundError

        with self.assertRaises(MemberNotFoundError) as ctx:
            split_from_dict(d, self.member_map, Decimal("100"), [self.alice, self.bob])
        self.assertIn("no longer an active member", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()