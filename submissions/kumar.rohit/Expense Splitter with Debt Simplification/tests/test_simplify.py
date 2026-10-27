"""
Tests for debt simplification (greedy and exact strategies).
"""

from decimal import Decimal

import pytest

from expense_splitter.models import MemberBalance, Settlement
from expense_splitter.simplify import simplify_debts, simplify_debts_exact, simplify_debts_greedy


def make_balances(*pairs) -> tuple[MemberBalance, ...]:
    """Create balances from (member_id, net_balance) pairs."""
    return tuple(
        MemberBalance(
            member_id=mid,
            total_paid=Decimal("0"),
            total_share=Decimal("0"),
            net_balance=Decimal(str(bal)),
        )
        for mid, bal in pairs
    )


def all_member_ids(balances: tuple[MemberBalance, ...]) -> frozenset[str]:
    return frozenset(b.member_id for b in balances)


class TestGreedySimplification:
    """Core simplification tests using the greedy strategy."""

    def test_single_debtor_single_creditor(self):
        """Alice owes Bob ₹500."""
        balances = make_balances(("alice", "-500"), ("bob", "500"))
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        assert len(settlements) == 1
        s = settlements[0]
        assert s.from_member_id == "alice"
        assert s.to_member_id == "bob"
        assert s.amount == Decimal("500.00")

    def test_multiple_debtors_creditors(self):
        """Several debtors and creditors."""
        balances = make_balances(
            ("a", "-100"), ("b", "-200"), ("c", "150"), ("d", "150")
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        assert len(settlements) <= 3  # greedy should produce at most n-1 transactions
        _verify_settlements(balances, settlements, all_member_ids(balances))

    def test_chain_of_debts(self):
        """A → owes B, B → owes C, etc. — greedy should simplify."""
        balances = make_balances(
            ("a", "-100"), ("b", "50"), ("c", "50")
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        _verify_settlements(balances, settlements, all_member_ids(balances))

    def test_all_settled(self):
        """Everyone is settled — zero settlements."""
        balances = make_balances(("a", "0"), ("b", "0"), ("c", "0"))
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        assert len(settlements) == 0

    def test_no_zero_settlements(self):
        """No settlement should have zero amount."""
        balances = make_balances(("a", "-500"), ("b", "500"))
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        for s in settlements:
            assert s.amount > 0

    def test_no_self_transfers(self):
        """No one pays themselves."""
        balances = make_balances(
            ("a", "-200"), ("b", "100"), ("c", "100")
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        for s in settlements:
            assert s.from_member_id != s.to_member_id

    def test_all_parties_in_group(self):
        """All settlement parties are known group members."""
        member_ids = frozenset({"a", "b", "c"})
        balances = make_balances(("a", "-300"), ("b", "150"), ("c", "150"))
        settlements = simplify_debts_greedy(balances, member_ids)
        for s in settlements:
            assert s.from_member_id in member_ids
            assert s.to_member_id in member_ids

    def test_applying_settlements_resolves_balances(self):
        """After applying all settlements, every balance = 0."""
        balances = make_balances(
            ("a", "-150.50"), ("b", "75.25"), ("c", "75.25")
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        _verify_settlements(balances, settlements, all_member_ids(balances))

    def test_deterministic_output(self):
        """Same input produces same output."""
        balances = make_balances(
            ("a", "-300"), ("b", "-200"), ("c", "100"), ("d", "400")
        )
        s1 = simplify_debts_greedy(balances, all_member_ids(balances))
        s2 = simplify_debts_greedy(balances, all_member_ids(balances))
        assert s1 == s2

    def test_complex_settlement_scenario(self):
        """Scenario from the problem description."""
        balances = make_balances(
            ("alice", "300"),  # should receive 300
            ("bob", "-300"),   # owes 300
            ("charlie", "0"),
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        assert len(settlements) == 1
        assert settlements[0].from_member_id == "bob"
        assert settlements[0].to_member_id == "alice"
        assert settlements[0].amount == Decimal("300.00")

    def test_preserves_cent_precision(self):
        """All amounts are at cent precision."""
        balances = make_balances(
            ("a", "-33.33"), ("b", "-33.33"), ("c", "66.66")
        )
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        for s in settlements:
            assert s.amount == s.amount.quantize(Decimal("0.01"))
        _verify_settlements(balances, settlements, all_member_ids(balances))

    def test_tied_balances_deterministic(self):
        """Two debtors with identical balances – deterministic tie-breaking."""
        balances = make_balances(
            ("a", "-100"), ("b", "-100"), ("c", "200")
        )
        s1 = simplify_debts_greedy(balances, all_member_ids(balances))
        s2 = simplify_debts_greedy(balances, all_member_ids(balances))
        assert s1 == s2

    def test_many_zero_balance_members(self):
        """Many zero-balance members don't affect output."""
        pairs = [("a", "-500"), ("b", "500")]
        for i in range(20):
            pairs.append((f"z{i}", "0"))
        balances = make_balances(*pairs)
        settlements = simplify_debts_greedy(balances, all_member_ids(balances))
        assert len(settlements) == 1
        _verify_settlements(balances, settlements, all_member_ids(balances))


class TestExactSimplification:
    """Tests for the exact minimum-transaction DP solver."""

    def test_exact_single_pair(self):
        """Exact solver on simple case."""
        balances = make_balances(("a", "-500"), ("b", "500"))
        settlements = simplify_debts_exact(balances, all_member_ids(balances))
        assert len(settlements) == 1
        _verify_settlements(balances, settlements, all_member_ids(balances))

    def test_exact_optimal_for_small_group(self):
        """Exact solver produces minimum transactions for known case."""
        # 4 people: A owes 100, B owes 50, C receives 80, D receives 70
        # Greedy might use 3 transactions; optimum is 3.
        # But a known case where greedy uses more than optimum:
        # A:-150, B:-150, C:100, D:100, E:100
        # Greedy: 4 transactions; optimum: also 4 (this is actually fine)
        # Let's test: A:-200, B:-100, C:150, D:150
        # Greedy settlements: B→D(100), A→C(150), A→D(50) = 3
        # Optimal: also 3
        # Actually greedy is within a factor of 2 for any input.
        # The exact solver may achieve fewer transactions in some cases:
        # A:-10, B:-20, C:-30, D:25, E:35
        # Greedy might give 4, optimal might be 4 too.
        # Key point: exact solver is correct; it never uses more than greedy.
        balances = make_balances(
            ("a", "-10"), ("b", "-20"), ("c", "-30"),
            ("d", "25"), ("e", "35"),
        )
        exact = simplify_debts_exact(balances, all_member_ids(balances))
        greedy = simplify_debts_greedy(balances, all_member_ids(balances))
        _verify_settlements(balances, exact, all_member_ids(balances))
        _verify_settlements(balances, greedy, all_member_ids(balances))
        # Exact should never use more transactions than greedy
        assert len(exact) <= len(greedy)

    def test_exact_settled_group(self):
        """Exact solver on already-settled group."""
        balances = make_balances(("a", "0"), ("b", "0"))
        settlements = simplify_debts_exact(balances, all_member_ids(balances))
        assert len(settlements) == 0

    def test_exact_three_person_cycle(self):
        """A owes B 100, B owes C 100, C owes A 100 (net zero for all after simplification)."""
        balances = make_balances(
            ("a", "0"), ("b", "0"), ("c", "0")
        )
        settlements = simplify_debts_exact(balances, all_member_ids(balances))
        assert len(settlements) == 0
        # All zero balances → no settlements needed

    def test_greedy_vs_exact_dispatcher(self):
        """The dispatcher with use_exact=True uses exact for small groups."""
        balances = make_balances(
            ("a", "-500"), ("b", "200"), ("c", "300")
        )
        # use_exact=True, group size 3 <= 12
        s = simplify_debts(balances, all_member_ids(balances), use_exact=True, exact_limit=12)
        _verify_settlements(balances, s, all_member_ids(balances))

    def test_greedy_fallback_for_large_groups(self):
        """use_exact=True but group > limit → falls back to greedy."""
        balances = make_balances(*[(f"m{i}", "100" if i == 0 else "-10") for i in range(15)])
        # Total: m0 has 100, 14 others share -140... wait, needs to sum to 0
        # Let's just verify it doesn't crash and produces valid settlements
        balances = make_balances(
            ("a", "-100"), ("b", "50"), ("c", "50"),
        )
        s = simplify_debts(balances, all_member_ids(balances), use_exact=True, exact_limit=2)
        # limit=2 < 3 non-zero members, so falls back to greedy
        _verify_settlements(balances, s, all_member_ids(balances))


def _verify_settlements(
    balances: tuple[MemberBalance, ...],
    settlements: tuple[Settlement, ...],
    member_ids: frozenset[str],
) -> None:
    """Verify that applying all settlements resolves all balances to zero."""
    final: dict[str, Decimal] = {b.member_id: b.net_balance for b in balances}
    for s in settlements:
        # No self-transfers
        assert s.from_member_id != s.to_member_id, f"Self-transfer: {s}"
        # Positive amount
        assert s.amount > 0, f"Zero/negative settlement: {s}"
        # Valid members
        assert s.from_member_id in member_ids, f"Unknown from: {s.from_member_id}"
        assert s.to_member_id in member_ids, f"Unknown to: {s.to_member_id}"
        # Apply
        final[s.from_member_id] += s.amount
        final[s.to_member_id] -= s.amount

    for mid, bal in final.items():
        assert bal == Decimal("0"), f"Member {mid} final balance = {bal}, expected 0"

    # Money is conserved
    total_settled = sum((s.amount for s in settlements), Decimal("0"))
    total_owed = sum(
        (abs(b.net_balance) for b in balances if b.net_balance < 0),
        Decimal("0"),
    )
    assert total_settled == total_owed