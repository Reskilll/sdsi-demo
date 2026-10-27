"""Input validation for expenses — M5 and edge cases."""

from __future__ import annotations

from typing import List, Set

from .models import Expense, SplitType


class ValidationError(Exception):
    """Raised when expense data fails validation."""


def validate_expense(expense: Expense, group_members: Set[str]) -> None:
    """Validate a single expense against the group. Raises ValidationError on any issue."""

    # ── Structural checks ──────────────────────────────────────────────
    if not expense.description or not expense.description.strip():
        raise ValidationError("Expense description must be non-empty.")

    if expense.total <= 0:
        raise ValidationError(
            f"Expense '{expense.description}': total must be positive, got {expense.total}."
        )

    if not expense.members:
        raise ValidationError(
            f"Expense '{expense.description}': member list must not be empty."
        )

    if expense.paid_by not in group_members:
        raise ValidationError(
            f"Expense '{expense.description}': payer '{expense.paid_by}' "
            f"is not in the group. Group members: {sorted(group_members)}"
        )

    unknown = set(expense.members) - group_members
    if unknown:
        raise ValidationError(
            f"Expense '{expense.description}': unknown members "
            f"{sorted(unknown)}. Group members: {sorted(group_members)}"
        )

    # ── Split-type-specific checks ─────────────────────────────────────
    n = len(expense.members)

    if expense.split_type == SplitType.EQUAL:
        return  # nothing extra to validate

    if expense.split_type == SplitType.EXACT:
        if not expense.amounts:
            raise ValidationError(
                f"Expense '{expense.description}': EXACT split requires 'amounts'."
            )
        if len(expense.amounts) != n:
            raise ValidationError(
                f"Expense '{expense.description}': expected {n} amounts for "
                f"{n} members, got {len(expense.amounts)}."
            )
        if any(a < 0 for a in expense.amounts):
            raise ValidationError(
                f"Expense '{expense.description}': amounts must be non-negative."
            )
        total_given = round(sum(expense.amounts), 2)
        if abs(total_given - expense.total) > 0.01:
            raise ValidationError(
                f"Expense '{expense.description}': exact amounts sum to "
                f"{total_given}, but expense total is {expense.total}."
            )
        return

    if expense.split_type == SplitType.PERCENTAGE:
        if not expense.amounts:
            raise ValidationError(
                f"Expense '{expense.description}': PERCENTAGE split requires 'amounts' (as percentages)."
            )
        if len(expense.amounts) != n:
            raise ValidationError(
                f"Expense '{expense.description}': expected {n} percentages for "
                f"{n} members, got {len(expense.amounts)}."
            )
        if any(p < 0 for p in expense.amounts):
            raise ValidationError(
                f"Expense '{expense.description}': percentages must be non-negative."
            )
        total_pct = round(sum(expense.amounts), 2)
        if abs(total_pct - 100.0) > 0.01:
            raise ValidationError(
                f"Expense '{expense.description}': percentages sum to "
                f"{total_pct}%, must sum to 100%."
            )
        return

    raise ValidationError(
        f"Expense '{expense.description}': unknown split type '{expense.split_type}'."
    )


def validate_group_input(group_name: str, members: List[str], expenses: List[dict]) -> None:
    """Validate the raw group input before constructing models.
    Catches structural issues early with clear messages."""

    errors: List[str] = []

    if not group_name or not group_name.strip():
        errors.append("Group name must be non-empty.")

    if not members:
        errors.append("Group must have at least one member.")
    elif len(members) != len(set(members)):
        errors.append("Duplicate member names found in group.")

    if not expenses:
        errors.append("Group must have at least one expense.")

    if errors:
        raise ValidationError("\n".join(errors))