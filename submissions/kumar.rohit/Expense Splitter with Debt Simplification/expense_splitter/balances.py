"""
Balance calculation – aggregate all expenses into per-member net balances.

net_balance = total_paid - total_share

- positive → member should receive money (is owed)
- negative → member owes money
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import (
    DEFAULT_CURRENCY,
    QUANTIZE_PREC,
    ROUNDING_MODE,
    Expense,
    ExpenseGroup,
    Member,
    MemberBalance,
    ShareAllocation,
)
from .splits import compute_shares


def calculate_balances(group: ExpenseGroup) -> tuple[MemberBalance, ...]:
    """
    Compute net balances for every group member.

    For each expense:
      - The payer is credited with the full expense amount (total_paid).
      - Each participant is debited their share (total_share).
      - A member who is both payer and participant gets both entries.

    Members with no participation in any expense appear with zero balances.
    """
    total_paid: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total_share: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for expense in group.expenses:
        shares = compute_shares(expense)
        total_paid[expense.payer_id] += expense.amount
        for pid, share in shares.shares.items():
            total_share[pid] += share

    balances: list[MemberBalance] = []
    for member in group.members:
        paid = total_paid.get(member.id, Decimal("0")).quantize(
            QUANTIZE_PREC, rounding=ROUNDING_MODE
        )
        share = total_share.get(member.id, Decimal("0")).quantize(
            QUANTIZE_PREC, rounding=ROUNDING_MODE
        )
        net = (paid - share).quantize(QUANTIZE_PREC, rounding=ROUNDING_MODE)
        balances.append(MemberBalance(member_id=member.id, total_paid=paid, total_share=share, net_balance=net))

    return tuple(balances)