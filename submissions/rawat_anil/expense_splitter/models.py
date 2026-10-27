"""Core data models for the expense splitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SplitType(str, Enum):
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


@dataclass
class Expense:
    """A single expense record."""

    description: str
    total: float
    paid_by: str
    split_type: SplitType
    members: List[str]
    # Only used for EXACT and PERCENTAGE splits
    amounts: Optional[List[float]] = None

    def __post_init__(self) -> None:
        if self.amounts is None:
            self.amounts = []


@dataclass
class Balance:
    """Each member's net position."""

    paid: float = 0.0
    owed: float = 0.0

    @property
    def net(self) -> float:
        """Positive → is owed money (creditor); negative → owes money (debtor)."""
        return self.paid - self.owed  # Positive = credit, Negative = debt


@dataclass
class Settlement:
    """A single simplified debt settlement instruction."""

    from_member: str
    to_member: str
    amount: float


@dataclass
class SplitResult:
    """The complete result of splitting a group's expenses."""

    group_name: str
    members: List[str]
    expenses: List[Expense]
    balances: Dict[str, Balance]
    settlements: List[Settlement]
    errors: List[str] = field(default_factory=list)