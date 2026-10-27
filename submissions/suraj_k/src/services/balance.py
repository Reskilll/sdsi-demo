"""
BalanceCalculator — pure functions that derive net positions from expenses.

No mutable state.  Callers pass in the expense list; they get back
a list of BalanceSnapshot objects keyed by member.
"""

from __future__ import annotations

from decimal import Decimal

from src.models.expense import Expense
from src.models.member import Member
from src.models.split import _quantize
from src.models.transaction import BalanceSnapshot


class BalanceCalculator:
    """Compute per-member net balances from a collection of expenses."""

    @staticmethod
    def compute(expenses: list[Expense]) -> list[BalanceSnapshot]:
        # Accumulate into dicts indexed by Member object.
        paid: dict[Member, Decimal] = {}
        owed: dict[Member, Decimal] = {}
        all_members: set[Member] = set()

        for expense in expenses:
            all_members.add(expense.payer)

            # Credit the payer.
            paid[expense.payer] = paid.get(expense.payer, Decimal("0")) + expense.total_amount

            # Debit each participant.
            shares = expense.split.shares()
            for member, share in shares.items():
                all_members.add(member)
                owed[member] = owed.get(member, Decimal("0")) + share

        snapshots: list[BalanceSnapshot] = []
        for member in all_members:
            p = _quantize(paid.get(member, Decimal("0")))
            o = _quantize(owed.get(member, Decimal("0")))
            net = _quantize(p - o)
            snapshots.append(
                BalanceSnapshot(member=member, paid=p, owed=o, net=net)
            )
        return snapshots

    @staticmethod
    def to_dicts(snapshots: list[BalanceSnapshot]) -> list[dict]:
        """JSON-serializable representation."""
        return [
            {
                "member": s.member.name,
                "paid": str(s.paid),
                "owed": str(s.owed),
                "net": str(s.net),
            }
            for s in snapshots
        ]