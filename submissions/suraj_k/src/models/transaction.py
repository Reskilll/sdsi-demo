"""
Transaction and BalanceSnapshot — output types for settlement.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.models.member import Member


@dataclass(frozen=True, slots=True)
class BalanceSnapshot:
    """Net position of a single member across all expenses."""

    member: Member
    paid: Decimal    # total this member paid (as expense payer)
    owed: Decimal    # total this member owes (from their share of splits)
    net: Decimal     # paid - owed  (+ means creditor, - means debtor)

    @property
    def is_creditor(self) -> bool:
        return self.net > Decimal("0")

    @property
    def is_debtor(self) -> bool:
        return self.net < Decimal("0")

    @property
    def is_settled(self) -> bool:
        return self.net == Decimal("0")


@dataclass(frozen=True, slots=True)
class Transaction:
    """A single settlement instruction: *from_member* pays *to_member*."""

    from_member: Member
    to_member: Member
    amount: Decimal