"""
Expense value object — immutable record of who paid, how much, and how it was split.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from src.errors import MemberNotFoundError, ValidationError
from src.models.member import Member
from src.models.split import EqualSplit, Split, validate_amount


class Expense:
    """A single expense in the group.

    Once constructed the object is logically immutable — all fields
    are read-only after the init guard runs.
    """

    __slots__ = ("id", "description", "payer", "total_amount", "split", "created_at")

    def __init__(
        self,
        description: str,
        payer: Member,
        total_amount: Decimal,
        split: Split | None = None,
    ) -> None:
        # Validate via the canonical guard (Edge Case 2: precision, range, >0).
        total = validate_amount(total_amount)

        if not isinstance(description, str) or not description.strip():
            raise ValidationError("Expense description must be a non-empty string")

        self.id: str = uuid.uuid4().hex
        self.description: str = description
        self.payer: Member = payer
        self.total_amount: Decimal = total

        # If no explicit split is given, construct an equal split with payer
        # as the sole participant.  This is a valid self-payment (Edge Case 4).
        if split is None:
            split = EqualSplit([payer], total_amount)

        self.split: Split = split
        self.created_at: datetime = datetime.now(timezone.utc)

        self._validate_payer_in_split()

    def _validate_payer_in_split(self) -> None:
        # Payer must be a participant.  Self-payment is legal (Edge Case 4).
        if self.payer not in self.split.participants:
            raise MemberNotFoundError(
                f"Payer '{self.payer.name}' must be among the split participants"
            )

    def __repr__(self) -> str:
        return (
            f"Expense(id={self.id[:8]}…, desc={self.description!r}, "
            f"payer={self.payer.name!r}, amount={self.total_amount})"
        )