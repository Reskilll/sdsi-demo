"""
Split calculation – determines each participant's share of an expense.

All monetary values are Decimal with round-half-up to two decimal places.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .exceptions import SplitError, ValidationError
from .models import (
    DEFAULT_CURRENCY,
    QUANTIZE_PREC,
    ROUNDING_MODE,
    ROUNDING_PRECISION,
    SUPPORTED_CURRENCIES,
    Expense,
    ShareAllocation,
    SplitEntry,
    SplitType,
)

# ── rounding helpers ──────────────────────────────────────────────────────────

def _round_amount(value: Decimal) -> Decimal:
    """Round a monetary amount to two decimal places using half-up."""
    return value.quantize(QUANTIZE_PREC, rounding=ROUNDING_MODE)


def _validate_currency(expense: Expense) -> None:
    if expense.currency not in SUPPORTED_CURRENCIES:
        raise ValidationError(
            f"Unsupported currency '{expense.currency}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}.",
            expense_id=expense.expense_id,
        )


# ── per-type split functions ──────────────────────────────────────────────────

def _split_equal(expense: Expense) -> ShareAllocation:
    """
    Divide *amount* equally among *participant_ids*.

    Rounding strategy (explained in README):
    1. Each participant gets floor(amount / n) at cent precision.
    2. The remainder (in cents) is distributed one cent at a time to the
       first N participants so that the total exactly equals the expense
       amount. This is deterministic and guarantees exact total.
    """
    n = len(expense.participant_ids)
    if n == 0:
        raise SplitError(f"Expense {expense.expense_id}: no participants for equal split")

    share = (expense.amount / n).quantize(ROUNDING_PRECISION, rounding=ROUNDING_MODE)
    allocated = share * n
    remainder = expense.amount - allocated

    # remainder should be a multiple of 0.01
    remainder_cents = int((remainder / Decimal("0.01")).to_integral_value())

    shares: dict[str, Decimal] = {}
    participant_list = list(expense.participant_ids)
    for i, pid in enumerate(participant_list):
        if i < remainder_cents:
            shares[pid] = share + Decimal("0.01")
        elif i < -remainder_cents:
            shares[pid] = share - Decimal("0.01")
        else:
            shares[pid] = share

    return ShareAllocation(expense_id=expense.expense_id, shares=shares)


def _split_exact(expense: Expense) -> ShareAllocation:
    """
    Use the exact amounts provided in *split_details*.
    """
    if not expense.split_details:
        raise SplitError(f"Expense {expense.expense_id}: split_details required for exact split")

    shares: dict[str, Decimal] = {}
    for entry in expense.split_details:
        shares[entry.member_id] = _round_amount(entry.value)

    return ShareAllocation(expense_id=expense.expense_id, shares=shares)


def _split_percentage(expense: Expense) -> ShareAllocation:
    """
    Convert percentage shares into monetary amounts.

    Rounding strategy:
    1. Each share = round(amount * percentage / 100, 2) using half-up.
    2. Distribute any rounding remainder (in paise) one cent at a time across
       participants in list order so the total equals exactly the expense amount.
    """
    if not expense.split_details:
        raise SplitError(f"Expense {expense.expense_id}: split_details required for percentage split")

    shares: dict[str, Decimal] = {}
    allocated = Decimal("0")
    for entry in expense.split_details:
        value = (expense.amount * entry.value / Decimal("100")).quantize(
            ROUNDING_PRECISION, rounding=ROUNDING_MODE
        )
        shares[entry.member_id] = value
        allocated += value

    remainder = expense.amount - allocated
    remainder_cents = int((remainder / Decimal("0.01")).to_integral_value())

    if remainder_cents != 0:
        direction = 1 if remainder_cents > 0 else -1
        for i, entry in enumerate(expense.split_details):
            if i >= abs(remainder_cents):
                break
            shares[entry.member_id] += Decimal("0.01") * direction

    return ShareAllocation(expense_id=expense.expense_id, shares=shares)


# ── dispatcher ────────────────────────────────────────────────────────────────

_SPLIT_HANDLERS = {
    SplitType.EQUAL: _split_equal,
    SplitType.EXACT: _split_exact,
    SplitType.PERCENTAGE: _split_percentage,
}


def compute_shares(expense: Expense) -> ShareAllocation:
    """
    Compute each participant's share for a single expense.

    Raises:
        ValidationError: unsupported currency.
        SplitError: invalid split configuration.
    """
    _validate_currency(expense)
    handler = _SPLIT_HANDLERS.get(expense.split_type)
    if handler is None:
        raise ValidationError(
            f"Unsupported split type: {expense.split_type.value}",
            expense_id=expense.expense_id,
        )
    return handler(expense)


def compute_all_shares(expenses: tuple[Expense, ...]) -> tuple[ShareAllocation, ...]:
    """Compute shares for every expense in a batch."""
    return tuple(compute_shares(e) for e in expenses)