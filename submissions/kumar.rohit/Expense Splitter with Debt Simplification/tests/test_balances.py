"""
Tests for balance calculation.
"""

from decimal import Decimal

from expense_splitter.balances import calculate_balances
from expense_splitter.models import Expense, ExpenseGroup, Member, SplitEntry, SplitType


def member(id_: str, name: str = "") -> Member:
    return Member(id=id_, name=name or id_)


class TestBalanceCalculation:
    """Core balance computation tests."""

    def test_single_equal_expense(self):
        """One equal-split expense: Alice pays ₹300 for Alice, Bob, Charlie."""
        group = ExpenseGroup(
            members=(member("alice"), member("bob"), member("charlie")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Dinner",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="alice",
                    participant_ids=("alice", "bob", "charlie"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}

        assert by_id["alice"].net_balance == Decimal("200.00")  # paid 300, share 100
        assert by_id["bob"].net_balance == Decimal("-100.00")
        assert by_id["charlie"].net_balance == Decimal("-100.00")

    def test_single_exact_expense(self):
        """One exact-split expense."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("1000.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EXACT,
                    split_details=(
                        SplitEntry("a", Decimal("200")),
                        SplitEntry("b", Decimal("300")),
                        SplitEntry("c", Decimal("500")),
                    ),
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}

        assert by_id["a"].net_balance == Decimal("800.00")  # paid 1000, share 200
        assert by_id["b"].net_balance == Decimal("-300.00")
        assert by_id["c"].net_balance == Decimal("-500.00")

    def test_single_percentage_expense(self):
        """One percentage-split expense: ₹1000 split 20/30/50."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("1000.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.PERCENTAGE,
                    split_details=(
                        SplitEntry("a", Decimal("20")),
                        SplitEntry("b", Decimal("30")),
                        SplitEntry("c", Decimal("50")),
                    ),
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}

        assert by_id["a"].net_balance == Decimal("800.00")  # paid 1000, share 200
        assert by_id["b"].net_balance == Decimal("-300.00")
        assert by_id["c"].net_balance == Decimal("-500.00")

    def test_multiple_expenses_different_payers(self):
        """Alice pays ₹500, Bob pays ₹300, both for same 3 people."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Exp1",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
                Expense(
                    expense_id="e2",
                    description="Exp2",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="b",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}

        # Alice paid 300, share 100+100=200, net = +100
        assert by_id["a"].net_balance == Decimal("100.00")
        # Bob paid 300, share 100+100=200, net = +100
        assert by_id["b"].net_balance == Decimal("100.00")
        # Charlie paid 0, share 100+100=200, net = -200
        assert by_id["c"].net_balance == Decimal("-200.00")

    def test_payer_not_participant(self):
        """Payer pays but does not participate."""
        group = ExpenseGroup(
            members=(member("a"), member("b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Gift",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("b",),  # only b participates
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}
        assert by_id["a"].net_balance == Decimal("100.00")  # paid 100, share 0
        assert by_id["b"].net_balance == Decimal("-100.00")

    def test_payer_also_participant(self):
        """Payer is also a participant."""
        group = ExpenseGroup(
            members=(member("a"), member("b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Lunch",
                    amount=Decimal("200.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}
        assert by_id["a"].net_balance == Decimal("100.00")  # paid 200, share 100
        assert by_id["b"].net_balance == Decimal("-100.00")

    def test_zero_balance_member(self):
        """Member who has no expenses appears with zero balance."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}
        assert "c" in by_id
        assert by_id["c"].net_balance == Decimal("0.00")
        assert by_id["c"].total_paid == Decimal("0.00")
        assert by_id["c"].total_share == Decimal("0.00")

    def test_mixed_balances(self):
        """Members with positive, negative, and zero balances."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c"), member("d")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("400.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EXACT,
                    split_details=(
                        SplitEntry("a", Decimal("200")),
                        SplitEntry("b", Decimal("100")),
                        SplitEntry("c", Decimal("100")),
                    ),
                ),
            ),
        )
        balances = calculate_balances(group)
        by_id = {b.member_id: b for b in balances}

        assert by_id["a"].net_balance > 0  # paid more than share
        assert by_id["b"].net_balance < 0  # owes
        assert by_id["c"].net_balance < 0  # owes
        assert by_id["d"].net_balance == 0  # not involved

    def test_already_settled_group(self):
        """Everyone pays exactly their share – all zero balances."""
        group = ExpenseGroup(
            members=(member("a"), member("b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a",),
                    split_type=SplitType.EQUAL,
                ),
                Expense(
                    expense_id="e2",
                    description="Test",
                    amount=Decimal("100.00"),
                    currency="INR",
                    payer_id="b",
                    participant_ids=("b",),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        for b in balances:
            assert b.net_balance == Decimal("0.00")


class TestBalanceInvariants:
    """Invariant checks on balance calculations."""

    def test_sum_of_balances_zero(self):
        """Sum of all net balances must be zero."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("1000.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        total = sum((b.net_balance for b in balances), Decimal("0"))
        assert total == Decimal("0.00")

    def test_sum_of_balances_zero_complex(self):
        """Sum zero with multiple expenses and split types."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Eq",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
                Expense(
                    expense_id="e2",
                    description="Ex",
                    amount=Decimal("600.00"),
                    currency="INR",
                    payer_id="b",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EXACT,
                    split_details=(
                        SplitEntry("a", Decimal("150")),
                        SplitEntry("b", Decimal("200")),
                        SplitEntry("c", Decimal("250")),
                    ),
                ),
                Expense(
                    expense_id="e3",
                    description="Pct",
                    amount=Decimal("500.00"),
                    currency="INR",
                    payer_id="c",
                    participant_ids=("a", "b"),
                    split_type=SplitType.PERCENTAGE,
                    split_details=(
                        SplitEntry("a", Decimal("40")),
                        SplitEntry("b", Decimal("60")),
                    ),
                ),
            ),
        )
        balances = calculate_balances(group)
        total = sum((b.net_balance for b in balances), Decimal("0"))
        assert total == Decimal("0.00")

    def test_total_shares_equal_total_expenses(self):
        """Sum of all members' total_share equals sum of all expenses."""
        group = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
                Expense(
                    expense_id="e2",
                    description="Test",
                    amount=Decimal("500.00"),
                    currency="INR",
                    payer_id="b",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        balances = calculate_balances(group)
        total_share = sum((b.total_share for b in balances), Decimal("0"))
        total_expenses = Decimal("800.00")
        assert total_share == total_expenses

    def test_order_independence(self):
        """Input ordering does not change financial results."""
        members = (member("a"), member("b"), member("c"))
        exp1 = Expense(
            expense_id="e1",
            description="First",
            amount=Decimal("300.00"),
            currency="INR",
            payer_id="a",
            participant_ids=("a", "b", "c"),
            split_type=SplitType.EQUAL,
        )
        exp2 = Expense(
            expense_id="e2",
            description="Second",
            amount=Decimal("500.00"),
            currency="INR",
            payer_id="b",
            participant_ids=("a", "b"),
            split_type=SplitType.EQUAL,
        )

        g1 = ExpenseGroup(members=members, expenses=(exp1, exp2))
        g2 = ExpenseGroup(members=members, expenses=(exp2, exp1))

        b1 = calculate_balances(g1)
        b2 = calculate_balances(g2)
        assert b1 == b2

    def test_member_order_independence(self):
        """Member order does not change results."""
        g1 = ExpenseGroup(
            members=(member("a"), member("b"), member("c")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        g2 = ExpenseGroup(
            members=(member("c"), member("a"), member("b")),
            expenses=(
                Expense(
                    expense_id="e1",
                    description="Test",
                    amount=Decimal("300.00"),
                    currency="INR",
                    payer_id="a",
                    participant_ids=("a", "b", "c"),
                    split_type=SplitType.EQUAL,
                ),
            ),
        )
        b1 = {b.member_id: b.net_balance for b in calculate_balances(g1)}
        b2 = {b.member_id: b.net_balance for b in calculate_balances(g2)}
        assert b1 == b2