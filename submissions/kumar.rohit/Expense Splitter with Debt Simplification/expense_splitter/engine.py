"""
Core engine – orchestrates split calculation, balance aggregation, and debt
simplification into a single pipeline.
"""

from __future__ import annotations

from decimal import Decimal

from .balances import calculate_balances
from .exceptions import ValidationError
from .models import ExpenseGroup, ExpenseResult, MemberBalance, Settlement
from .simplify import simplify_debts


def process_group(
    group: ExpenseGroup,
    use_exact: bool = False,
    exact_limit: int = 12,
) -> ExpenseResult:
    """
    Process an expense group: calculate balances, then simplify debts.

    Args:
        group: A validated ExpenseGroup.
        use_exact: If True, use exact minimum-transaction DP solver for small groups.
        exact_limit: Maximum group size for exact solver.

    Returns:
        ExpenseResult with balances, settlements, and summary info.
    """
    balances = calculate_balances(group)
    settlements = simplify_debts(
        balances, group.member_ids, use_exact=use_exact, exact_limit=exact_limit
    )

    # Verify invariants
    _verify_balances_zero_sum(balances)
    _verify_settlements(balances, settlements, group.member_ids)

    return ExpenseResult(
        balances=balances,
        settlements=settlements,
        expense_count=len(group.expenses),
        member_count=len(group.members),
    )


def _verify_balances_zero_sum(balances: tuple[MemberBalance, ...]) -> None:
    """Verify that all net balances sum to zero."""
    total = sum((b.net_balance for b in balances), Decimal("0"))
    if total != 0:
        raise RuntimeError(
            f"Invariant violated: sum of net balances is {total}, expected 0"
        )


def _verify_settlements(
    balances: tuple[MemberBalance, ...],
    settlements: tuple[Settlement, ...],
    member_ids: frozenset[str],
) -> None:
    """Verify that settlements are valid and resolve all balances."""
    # Check no self-transfers, zero amounts, or unknown members
    for s in settlements:
        if s.from_member_id == s.to_member_id:
            raise RuntimeError(f"Self-transfer detected: {s.from_member_id}")
        if s.amount <= 0:
            raise RuntimeError(f"Zero/negative settlement: {s.amount}")
        if s.from_member_id not in member_ids:
            raise RuntimeError(f"Unknown debtor: {s.from_member_id}")
        if s.to_member_id not in member_ids:
            raise RuntimeError(f"Unknown creditor: {s.to_member_id}")

    # Verify settlements resolve balances
    final: dict[str, Decimal] = {b.member_id: b.net_balance for b in balances}
    for s in settlements:
        final[s.from_member_id] += s.amount
        final[s.to_member_id] -= s.amount

    for mid, bal in final.items():
        if bal != 0:
            raise RuntimeError(
                f"Invariant violated: member '{mid}' final balance is {bal}, expected 0"
            )