"""
SettlementEngine — greedy max-heap debt simplification algorithm.

Given a list of net balances, produces the minimum set of transactions
needed to settle all debts.  This is the Splitwise "simplify debts" algorithm.

Runtime: O(n log n) where n is the number of members with non-zero balances.
"""

from __future__ import annotations

import heapq
from decimal import Decimal

from src.models.transaction import BalanceSnapshot, Transaction


# Threshold below which a balance is treated as zero (handles rounding residue).
EPSILON = Decimal("0.005")


class SettlementEngine:
    """Compute the minimal set of settlements from net balances."""

    @staticmethod
    def simplify(balances: list[BalanceSnapshot]) -> list[Transaction]:
        """Greedy max-heap algorithm for minimum transactions.

        Builds a max-heap of creditors and a max-heap of debtors,
        then repeatedly matches the largest creditor with the largest debtor.
        """
        # Separate into creditors (net > 0) and debtors (net < 0).
        # Use negative values for max-heap behaviour (heapq is a min-heap).
        creditors: list[tuple[Decimal, str, BalanceSnapshot]] = []  # (-net, tie-break, snapshot)
        debtors: list[tuple[Decimal, str, BalanceSnapshot]] = []    # (net, tie-break, snapshot)

        for b in balances:
            if b.net > EPSILON:
                # Push negative so the largest net comes out first.
                heapq.heappush(creditors, (-b.net, b.member.name, b))
            elif b.net < -EPSILON:
                # For debtors, net is already negative; push abs for max-heap.
                heapq.heappush(debtors, (b.net, b.member.name, b))

        transactions: list[Transaction] = []

        while creditors and debtors:
            neg_credit, _, c_snap = heapq.heappop(creditors)
            neg_debit, _, d_snap = heapq.heappop(debtors)

            credit_amt = -neg_credit   # positive amount the creditor is owed
            debit_amt = -neg_debit     # positive amount the debtor owes

            settle_amt = min(credit_amt, debit_amt)
            # Round to 2 decimal places to keep everything clean.
            settle_cents = settle_amt.quantize(Decimal("0.01"))

            if settle_cents > Decimal("0"):
                transactions.append(
                    Transaction(from_member=d_snap.member, to_member=c_snap.member, amount=settle_cents)
                )

            # Push remainders back.
            remainder = credit_amt - settle_amt
            if remainder > EPSILON:
                heapq.heappush(creditors, (-remainder, c_snap.member.name, c_snap))

            remainder = debit_amt - settle_amt
            if remainder > EPSILON:
                heapq.heappush(debtors, (-remainder, d_snap.member.name, d_snap))

        return transactions