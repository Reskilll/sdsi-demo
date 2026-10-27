"""Net-balance computation for the group (M2)."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .models import Expense, SplitType

_ROUND_PLACES = 2


def compute_balances(expenses: List[Expense]) -> Dict[str, float]:
    """Return ``{member: net_balance}`` where +ve means *owed money*.

    For each expense:
      - The payer effectively lends the full amount to the group.
      - Each participant (including the payer) owes their share.
      - Net = total paid by member – total owed by member.
    """
    paid: Dict[str, float] = defaultdict(float)
    owed: Dict[str, float] = defaultdict(float)

    for exp in expenses:
        # The payer fronted the whole amount.
        paid[exp.paid_by] += exp.total_amount

        shares = _compute_shares(exp)
        for member, share in shares.items():
            owed[member] += share

    # Gather every person we've seen.
    all_members = set(paid.keys()) | set(owed.keys())

    balances: Dict[str, float] = {}
    for m in all_members:
        net = paid.get(m, 0.0) - owed.get(m, 0.0)
        balances[m] = round(net, _ROUND_PLACES)

    return balances


def _compute_shares(expense: Expense) -> Dict[str, float]:
    """Distribute *expense.total_amount* across participants per the split rule."""
    total = expense.total_amount
    participants = list(dict.fromkeys(expense.participants))
    shares: Dict[str, float] = {}

    if expense.split_type == SplitType.EQUAL:
        share = total / len(participants)
        for p in participants:
            shares[p] = share

    elif expense.split_type == SplitType.EXACT:
        # Use provided amounts; missing members default to 0.
        for p in participants:
            shares[p] = float(expense.splits.get(p, 0))

    elif expense.split_type == SplitType.PERCENTAGE:
        # Percentages are guaranteed to sum to 100 by validation.
        for p in participants:
            pct = float(expense.splits.get(p, 0))
            shares[p] = round(total * pct / 100.0, _ROUND_PLACES)

    # Round every share for consistency.
    return {k: round(v, _ROUND_PLACES) for k, v in shares.items()}