"""Domain models for expense splitting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class SplitType(str, Enum):
    """Supported split strategies."""

    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


@dataclass
class Expense:
    """One logged expense inside a group."""

    description: str
    paid_by: str
    total_amount: float
    split_type: SplitType
    participants: List[str]
    splits: Dict[str, float] = field(default_factory=dict)


@dataclass
class Settlement:
    """A directed payment that simplifies the group debt."""

    from_member: str
    to_member: str
    amount: float


@dataclass
class SplitResult:
    """Final output: per-person balances and the simplified settlement list."""

    balances: Dict[str, float]
    settlements: List[Settlement]
    expenses_processed: int = 0
    errors: List[str] = field(default_factory=list)