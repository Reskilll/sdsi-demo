"""Balance computation and greedy debt-simplification engine."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from .models import Balance, Expense, Settlement, SplitType


def compute_balances(expenses: List[Expense], members: List[str]) -> Dict[str, Balance]:
    """Walk every expense and tally each member's paid vs owed."""

    balances: Dict[str, Balance] = {m: Balance() for m in members}

    for exp in expenses:
        n = len(exp.members)

        if exp.split_type == SplitType.EQUAL:
            per_person = round(exp.total / n, 2)
            # Handle rounding: last member absorbs the difference
            shares = [per_person] * n
            diff = round(exp.total - sum(shares), 2)
            shares[-1] = round(shares[-1] + diff, 2)
        elif exp.split_type == SplitType.EXACT:
            shares = list(exp.amounts)  # type: ignore[arg-type]
        elif exp.split_type == SplitType.PERCENTAGE:
            shares = []
            for pct in exp.amounts:  # type: ignore[union-attr]
                share = round(exp.total * pct / 100.0, 2)
                shares.append(share)
            # Absorb rounding error into the last non-zero share
            diff = round(exp.total - sum(shares), 2)
            if diff != 0:
                shares[-1] = round(shares[-1] + diff, 2)
        else:
            continue  # pragma: no cover — caught by validation

        # Apply shares
        for member, share in zip(exp.members, shares):
            balances[member].owed += share

        balances[exp.paid_by].paid += exp.total

    # Round everything to 2 decimal places to kill floating-point noise
    for bal in balances.values():
        bal.paid = round(bal.paid, 2)
        bal.owed = round(bal.owed, 2)

    return balances


def simplify_debts(balances: Dict[str, Balance]) -> List[Settlement]:
    """Greedy debt simplification: produces a minimal or near-minimal settlement list.

    Algorithm:
    1. Compute net positions: positive = creditor, negative = debtor.
    2. While there are unsettled parties, match the largest debtor with the
       largest creditor. The smaller magnitude determines the settlement size.
    3. Repeat until all positions are zero (within float tolerance).
    """

    # Build net positions, excluding members with ~zero balance
    net: List[Tuple[str, float]] = []
    for name, bal in balances.items():
        pos = round(bal.net, 2)
        if abs(pos) > 0.005:
            net.append((name, pos))

    settlements: List[Settlement] = []

    # Greedy settle: O(n²) worst-case but optimal for small real-world groups
    while net:
        # Re-sort: debtors (most negative) first, creditors (most positive) last
        net.sort(key=lambda x: x[1])

        debtor_name, debtor_amt = net[0]   # most negative
        creditor_name, creditor_amt = net[-1]  # most positive

        if abs(debtor_amt) < 0.005 or abs(creditor_amt) < 0.005:
            break  # settled within tolerance

        settlement_amount = round(min(-debtor_amt, creditor_amt), 2)

        if settlement_amount > 0:
            settlements.append(Settlement(
                from_member=debtor_name,
                to_member=creditor_name,
                amount=settlement_amount,
            ))

        # Update positions
        new_debtor = round(debtor_amt + settlement_amount, 2)
        new_creditor = round(creditor_amt - settlement_amount, 2)

        # Rebuild list with updated values, dropping zeros
        net = [(name, new_debtor if name == debtor_name else pos) for name, pos in net[1:-1]]
        if abs(new_debtor) > 0.005:
            net.append((debtor_name, new_debtor))
        if abs(new_creditor) > 0.005:
            net.append((creditor_name, new_creditor))

    return settlements