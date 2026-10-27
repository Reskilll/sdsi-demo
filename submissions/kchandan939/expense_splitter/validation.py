"""Input validation for expense data (M5)."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .models import Expense, SplitType

# Acceptable floating-point drift for monetary amounts (one paisa).
_TOLERANCE = 0.015


def validate_expense(expense: Expense) -> Optional[str]:
    """Return the first hard-error string, or ``None`` if the expense is usable.

    Hard errors (expense **must** be skipped):
      - payer not a participant
      - empty participants
      - negative total
      - exact splits don't sum to total
      - percentages don't sum to 100
      - negative split amounts
      - unknown split_type
      - equal split provided splits

    Soft warnings (expense is still processed, defaults applied):
      - missing participant in exact/percentage split → treated as ₹0 / 0%
    """
    err, _warn = validate_expense_full(expense)
    return err


def validate_expense_full(expense: Expense) -> Tuple[Optional[str], Optional[str]]:
    """Full validation returning ``(hard_error, soft_warning)`` tuples.

    Only one error is returned — we report the first hard failure found.
    """
    # --- participants integrity ------------------------------------------------
    if not isinstance(expense.participants, list):
        return "participants must be a list", None
    participants = list(dict.fromkeys(expense.participants))  # deduplicate
    if len(participants) < 1:
        return "at least one participant is required", None

    if not isinstance(expense.description, str) or not expense.description.strip():
        return "description must be a non-empty string", None

    if not isinstance(expense.paid_by, str) or not expense.paid_by.strip():
        return "paid_by must be a non-empty string", None

    if expense.paid_by not in participants:
        return f"payer '{expense.paid_by}' is not a participant: {participants}", None

    # --- total amount ----------------------------------------------------------
    if not isinstance(expense.total_amount, (int, float)):
        return "total_amount must be a number", None
    if expense.total_amount < 0:
        return "total_amount must not be negative", None

    # --- splits payload --------------------------------------------------------
    if not isinstance(expense.splits, dict):
        return "splits must be a dict (member → value)", None

    # Equal split has no further constraints (any empty splits dict is fine).
    if expense.split_type == SplitType.EQUAL:
        if expense.splits:
            return "equal split must not provide per-member splits", None
        return None, None

    # --- all split keys must be participants -----------------------------------
    unknown = [m for m in expense.splits if m not in participants]
    if unknown:
        return f"splits reference non-participants: {unknown}", None

    warning: Optional[str] = None

    if expense.split_type == SplitType.EXACT:
        err = _validate_exact(expense)
        if err:
            return err, None
        # Soft warning for missing participants (gracefully defaulted to ₹0).
        missing = [p for p in participants if p not in expense.splits]
        if missing:
            warning = (
                f"exact split missing amounts for: {missing} "
                f"(treated as ₹0)"
            )
        return None, warning

    if expense.split_type == SplitType.PERCENTAGE:
        err = _validate_percentage(expense)
        if err:
            return err, None
        # Soft warning for missing participants (gracefully defaulted to 0%).
        missing = [p for p in participants if p not in expense.splits]
        if missing:
            warning = (
                f"percentage split missing values for: {missing} "
                f"(treated as 0%)"
            )
        return None, warning

    return f"unknown split_type: {expense.split_type}", None


def _validate_exact(expense: Expense) -> Optional[str]:
    if not expense.splits:
        return "exact split requires per-member amounts"

    total = expense.total_amount
    split_sum = 0.0
    for member, amt in expense.splits.items():
        if not isinstance(amt, (int, float)):
            return f"exact split amount for '{member}' is not a number"
        if amt < 0:
            return f"exact split amount for '{member}' is negative"
        split_sum += float(amt)

    if not math.isclose(split_sum, total, abs_tol=_TOLERANCE):
        return (
            f"exact split amounts ({split_sum:.2f}) "
            f"do not sum to total ({total:.2f})"
        )
    return None


def _validate_percentage(expense: Expense) -> Optional[str]:
    if not expense.splits:
        return "percentage split requires per-member percentages"

    pct_sum = 0.0
    for member, pct in expense.splits.items():
        if not isinstance(pct, (int, float)):
            return f"percentage split value for '{member}' is not a number"
        if pct < 0:
            return f"percentage split value for '{member}' is negative"
        pct_sum += float(pct)

    if not math.isclose(pct_sum, 100.0, abs_tol=_TOLERANCE):
        return (
            f"percentage splits sum to {pct_sum:.2f}%, expected 100%"
        )
    return None


def validate_expenses(expenses: list) -> List[str]:
    """Batch-validate raw expense dicts; returns list of error strings."""
    errors: List[str] = []
    if not isinstance(expenses, list):
        return ["input must be a list of expenses"]
    if not expenses:
        return ["expenses list is empty"]
    for i, raw in enumerate(expenses):
        if not isinstance(raw, dict):
            errors.append(f"[{i}] expense is not a JSON object")
            continue
        try:
            exp = _parse_expense(raw)
        except (TypeError, ValueError) as exc:
            errors.append(f"[{i}] parse error: {exc}")
            continue
        err = validate_expense(exp)
        if err:
            errors.append(f"[{i}] '{raw.get('description', '?')}': {err}")
    return errors


def _parse_expense(raw: dict) -> Expense:
    """Coerce a raw JSON dict into an Expense model."""
    st_raw = raw.get("split_type", "equal")
    try:
        split_type = SplitType(st_raw)
    except ValueError:
        raise ValueError(f"invalid split_type: {st_raw!r}") from None

    participants = _ensure_str_list(raw.get("participants", []))

    splits = {}
    raw_splits = raw.get("splits", {})
    if isinstance(raw_splits, dict):
        for k, v in raw_splits.items():
            splits[str(k)] = float(v)

    return Expense(
        description=str(raw.get("description", "")).strip(),
        paid_by=str(raw.get("paid_by", "")).strip(),
        total_amount=float(raw.get("total_amount", 0)),
        split_type=split_type,
        participants=participants,
        splits=splits,
    )


def _ensure_str_list(val) -> List[str]:
    if not isinstance(val, list):
        raise TypeError("participants must be a list")
    return [str(v) for v in val]