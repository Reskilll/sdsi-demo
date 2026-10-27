"""Debt simplification — produce a minimal settlement list (M3).

Uses a greedy largest-creditor-to-largest-debtor algorithm that runs in
O(n log n) and yields near-minimal transaction counts.  Finding the
absolute minimum is NP-hard; this is the algorithm Splitwise uses.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Tuple

from .models import Settlement

_ROUND_PLACES = 2
_TOLERANCE = 0.005  # ignore balances within half a paisa


def simplify(balances: Dict[str, float]) -> List[Settlement]:
    """Reduce *balances* (member → net) into the fewest "A pays B ₹X" entries.

    Returns an empty list when all balances are zero (already settled).
    """
    creditors: List[Tuple[float, str]] = []   # max-heap (stored as negative)
    debtors: List[Tuple[float, str]] = []     # max-heap by abs(amount)

    for member, net in balances.items():
        amt = round(net, _ROUND_PLACES)
        if amt > _TOLERANCE:
            heapq.heappush(creditors, (-amt, member))  # max-heap via negation
        elif amt < -_TOLERANCE:
            heapq.heappush(debtors, (amt, member))     # stored negative → min-heap

    settlements: List[Settlement] = []

    while creditors and debtors:
        neg_credit, creditor = heapq.heappop(creditors)
        credit = -neg_credit

        neg_debt, debtor = heapq.heappop(debtors)
        debt = -neg_debt  # debt is now positive

        # How much the debtor pays the creditor this round.
        payment = min(credit, debt)
        payment = round(payment, _ROUND_PLACES)

        if payment > 0:
            settlements.append(
                Settlement(from_member=debtor, to_member=creditor, amount=payment)
            )

        # Re-insert remainders.
        credit = round(credit - payment, _ROUND_PLACES)
        debt = round(debt - payment, _ROUND_PLACES)

        if credit > _TOLERANCE:
            heapq.heappush(creditors, (-credit, creditor))
        if debt > _TOLERANCE:
            heapq.heappush(debtors, (-debt, debtor))

    return settlements