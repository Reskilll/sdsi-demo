"""
Data models for the expense splitter application.

All monetary amounts are stored as Decimal to avoid floating-point errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

# Supported currencies. We preserve the domain concept but only one currency
# is currently supported — mixing currencies raises a validation error.
SUPPORTED_CURRENCIES = frozenset({"INR"})
DEFAULT_CURRENCY = "INR"

# Two decimal places for INR (paise). The rounding mode is half-up (banker's
# rounding would be ROUND_HALF_EVEN, but standard consumer finance uses half-up).
ROUNDING_PRECISION = Decimal("0.01")
QUANTIZE_PREC = Decimal("0.01")
ROUNDING_MODE = ROUND_HALF_UP

# Sensible limits to guard against absurd inputs.
MAX_MEMBER_COUNT = 10_000
MAX_EXPENSE_COUNT = 50_000
MAX_AMOUNT = Decimal("9_999_999_999.99")
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class SplitType(str, Enum):
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


@dataclass(frozen=True)
class Member:
    """A group member identified by a unique string ID."""

    id: str
    name: Optional[str] = None

    def __str__(self) -> str:
        return self.name if self.name else self.id


@dataclass(frozen=True)
class SplitEntry:
    """One participant's share in an expense (for exact / percentage splits)."""

    member_id: str
    value: Decimal  # amount for 'exact', percentage for 'percentage'


@dataclass(frozen=True)
class Expense:
    """A single shared expense."""

    expense_id: str
    description: str
    amount: Decimal
    currency: str
    payer_id: str
    participant_ids: tuple[str, ...]
    split_type: SplitType
    split_details: tuple[SplitEntry, ...] = field(default_factory=tuple)
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError(f"Expense {self.expense_id}: amount must be positive")


@dataclass(frozen=True)
class ExpenseGroup:
    """A group of members with a collection of expenses."""

    members: tuple[Member, ...]
    expenses: tuple[Expense, ...]

    @property
    def member_ids(self) -> frozenset[str]:
        return frozenset(m.id for m in self.members)

    @property
    def member_map(self) -> dict[str, Member]:
        return {m.id: m for m in self.members}


@dataclass(frozen=True)
class MemberBalance:
    """Net balance for a single member."""

    member_id: str
    total_paid: Decimal
    total_share: Decimal
    net_balance: Decimal  # positive = to receive, negative = owes


@dataclass(frozen=True)
class Settlement:
    """A single settlement instruction."""

    from_member_id: str  # debtor (owes money)
    to_member_id: str     # creditor (should receive)
    amount: Decimal


@dataclass(frozen=True)
class ExpenseResult:
    """Complete result of processing an expense group."""

    balances: tuple[MemberBalance, ...]
    settlements: tuple[Settlement, ...]
    expense_count: int
    member_count: int
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ShareAllocation:
    """Per-member share allocation for a single expense."""

    expense_id: str
    shares: dict[str, Decimal]