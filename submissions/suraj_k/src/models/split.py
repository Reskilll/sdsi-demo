"""
Split strategy hierarchy — Equal, Exact, Percentage.

Each subclass knows how to validate its own invariants and
how to compute the share a given participant owes.

Shares are computed once and cached, guaranteeing that
share_for(member) and shares()[member] always agree.
"""

from __future__ import annotations

import abc
from decimal import Context
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Mapping

from src.errors import SplitValidationError, ValidationError
from src.models.member import Member

# ---------------------------------------------------------------------------
# Decimal precision policy
#   prec=28  → covers ₹99,999,999,999.99 with room to spare
#   rounding → ROUND_HALF_UP (halves round up)
#   traps=[] → no implicit exceptions; we quantize explicitly
# ---------------------------------------------------------------------------
MONEY_CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP, traps=[])

TWO_PLACES = Decimal("0.01")
EPSILON = Decimal("0.005")

# ~₹100 billion cap — prevents overflow and unreasonable inputs.
MAX_AMOUNT = Decimal("99999999999.99")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP, context=MONEY_CONTEXT)


# ---------------------------------------------------------------------------
# Centralised input amount guard (shared by Expense and JSON processor)
# ---------------------------------------------------------------------------

def validate_amount(raw_value) -> Decimal:
    """Parse, validate, and quantize a monetary amount.

    Rejects: non-numeric, sub-paisa precision, NaN, Inf, ≤0, >MAX.
    Returns a quantized Decimal.
    """
    try:
        d = Decimal(str(raw_value))
    except Exception as exc:
        raise ValidationError(f"{raw_value!r} is not a valid monetary amount") from exc

    # Guard against NaN / Infinity (Decimal(str()) may still produce these).
    if not d.is_finite():
        raise ValidationError(f"{raw_value!r} is not a finite number")

    if d.as_tuple().exponent < -2:
        raise ValidationError(
            f"Amount {d} has sub-paisa precision (max 2 decimal places)"
        )

    d = _quantize(d)
    if d <= Decimal("0"):
        raise ValidationError(f"Amount must be positive, got {d}")
    if d > MAX_AMOUNT:
        raise ValidationError(f"Amount {d} exceeds maximum ({MAX_AMOUNT})")

    return d


# ---------------------------------------------------------------------------
# Split — Abstract Strategy
# ---------------------------------------------------------------------------

class Split(abc.ABC):
    """Abstract strategy for dividing an expense across participants.

    Shares are cached on first access so share_for() ≡ shares()[member].
    """

    def __init__(self, participants: list[Member], total_amount: Decimal) -> None:
        if len(participants) < 1:
            raise SplitValidationError(
                f"At least 1 participant required, got {len(participants)}"
            )

        # Detect duplicate participants (unlisted edge case).
        seen: set[str] = set()
        for m in participants:
            if m.id in seen:
                raise SplitValidationError(
                    f"Duplicate participant '{m.name}' in split"
                )
            seen.add(m.id)

        self.participants: list[Member] = participants
        self.total_amount: Decimal = _quantize(total_amount)
        self._cached_shares: dict[Member, Decimal] | None = None

    # ---- public API ----

    def share_for(self, member: Member) -> Decimal:
        if self._cached_shares is None:
            self._cached_shares = self._compute_shares()
        return self._cached_shares.get(member, Decimal("0.00"))

    def shares(self) -> dict[Member, Decimal]:
        if self._cached_shares is None:
            self._cached_shares = self._compute_shares()
        return dict(self._cached_shares)

    # ---- subclass contract ----

    @abc.abstractmethod
    def _compute_shares(self) -> dict[Member, Decimal]:
        """Compute participant→amount dict.  Called once, cached."""

    @abc.abstractmethod
    def _validate_invariants(self) -> None:
        """Raise SplitValidationError on violation."""


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class EqualSplit(Split):
    """Evenly divide total across all participants.

    Rounding residue from ₹100/3 → 33.33+33.33+33.34 is absorbed
    by the *last* participant so Σ shares = total.
    """

    def __init__(self, participants: list[Member], total_amount: Decimal) -> None:
        super().__init__(participants, total_amount)
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        pass  # no further invariants

    def _compute_shares(self) -> dict[Member, Decimal]:
        n = len(self.participants)
        if n == 0:
            return {}
        base = _quantize(self.total_amount / n)
        result: dict[Member, Decimal] = {m: base for m in self.participants}
        allocated = _quantize(base * n)
        residue = self.total_amount - allocated
        if residue != Decimal("0"):
            last = self.participants[-1]
            result[last] = _quantize(result[last] + residue)
        return result


class ExactSplit(Split):
    """Each participant pays a pre-specified exact amount.

    Invariants:
      Σ amounts == total
      Every individual amount ≥ 0 (you can't owe negative money)
    """

    def __init__(
        self,
        participants: list[Member],
        total_amount: Decimal,
        amounts: Mapping[Member, Decimal],
    ) -> None:
        super().__init__(participants, total_amount)
        self._amounts: dict[Member, Decimal] = {}
        for m in participants:
            raw = Decimal(str(amounts[m]))
            if raw < Decimal("0"):
                raise SplitValidationError(
                    f"Exact amount for '{m.name}' is negative ({raw}); all amounts must be ≥ 0"
                )
            self._amounts[m] = _quantize(raw)
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        actual = _quantize(sum(self._amounts.values(), Decimal("0")))
        if actual != self.total_amount:
            raise SplitValidationError(
                f"Exact amounts sum to {actual}, expected total {self.total_amount}"
            )

    def _compute_shares(self) -> dict[Member, Decimal]:
        return dict(self._amounts)


class PercentageSplit(Split):
    """Each participant pays a percentage of the total.

    Invariants:
      Σ percentages == 100
      Every individual percentage ≥ 0
    """

    def __init__(
        self,
        participants: list[Member],
        total_amount: Decimal,
        percentages: Mapping[Member, Decimal],
    ) -> None:
        super().__init__(participants, total_amount)
        self._percentages: dict[Member, Decimal] = {}
        for m in participants:
            raw = Decimal(str(percentages[m]))
            if raw < Decimal("0"):
                raise SplitValidationError(
                    f"Percentage for '{m.name}' is negative ({raw}); all percentages must be ≥ 0"
                )
            self._percentages[m] = _quantize(raw)
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        actual = _quantize(sum(self._percentages.values(), Decimal("0")))
        expected = Decimal("100")
        if actual != expected:
            raise SplitValidationError(
                f"Percentages sum to {actual}%, expected {expected}%"
            )

    def _compute_shares(self) -> dict[Member, Decimal]:
        n = len(self.participants)
        if n == 0:
            return {}
        result: dict[Member, Decimal] = {}
        allocated = Decimal("0")
        for i, m in enumerate(self.participants):
            pct = self._percentages[m]
            if i == n - 1:
                share = self.total_amount - allocated
            else:
                share = _quantize(self.total_amount * pct / Decimal("100"))
                allocated += share
            result[m] = _quantize(share)
        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def split_from_dict(
    split_data: dict,
    member_map: dict[str, Member],
    total_amount: Decimal,
    _all_members: list[Member] | None = None,
) -> Split:
    """Build a Split instance from a JSON-like dict.

    _all_members is no longer used but kept for backward API compat.
    """
    from src.errors import MemberNotFoundError

    split_type = split_data.get("type", "equal")
    participant_names: list[str] = split_data.get("participants", [])

    if len(participant_names) < 1:
        raise SplitValidationError("At least 1 participant required in split")

    # Duplicate-names-in-split guard (unlisted edge case).
    if len(set(participant_names)) != len(participant_names):
        raise SplitValidationError("Duplicate participant names in split")

    participants: list[Member] = []
    for name in participant_names:
        m = member_map.get(name)
        if m is None:
            raise MemberNotFoundError(f"Participant '{name}' is not a member of the group")
        if not m.is_active:
            raise MemberNotFoundError(
                f"Participant '{name}' is no longer an active member"
            )
        participants.append(m)

    if split_type == "equal":
        return EqualSplit(participants, total_amount)

    elif split_type == "exact":
        raw_amounts = split_data.get("amounts")
        if raw_amounts is None:
            raise SplitValidationError("Exact split requires 'amounts' field")
        amounts: dict[Member, Decimal] = {}
        for name in participant_names:
            if name not in raw_amounts:
                raise SplitValidationError(f"Exact split missing amount for '{name}'")
            m = member_map[name]
            amounts[m] = Decimal(str(raw_amounts[name]))
        return ExactSplit(participants, total_amount, amounts)

    elif split_type == "percentage":
        raw_pcts = split_data.get("percentages")
        if raw_pcts is None:
            raise SplitValidationError("Percentage split requires 'percentages' field")
        percentages: dict[Member, Decimal] = {}
        for name in participant_names:
            if name not in raw_pcts:
                raise SplitValidationError(f"Percentage split missing percentage for '{name}'")
            m = member_map[name]
            percentages[m] = Decimal(str(raw_pcts[name]))
        return PercentageSplit(participants, total_amount, percentages)

    else:
        raise SplitValidationError(
            f"Unknown split type '{split_type}'. Use: equal, exact, percentage"
        )