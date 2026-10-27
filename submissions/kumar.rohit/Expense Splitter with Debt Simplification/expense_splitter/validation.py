"""
Input validation – validate expense group data at the boundary.

All JSON input is treated as untrusted. This module performs exhaustive
validation before any business logic runs.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .exceptions import ValidationError, ValidationReport
from .models import (
    DEFAULT_CURRENCY,
    MAX_AMOUNT,
    MAX_EXPENSE_COUNT,
    MAX_FILE_SIZE_BYTES,
    MAX_MEMBER_COUNT,
    ROUNDING_PRECISION,
    SUPPORTED_CURRENCIES,
    Expense,
    ExpenseGroup,
    Member,
    SplitEntry,
    SplitType,
)


def validate_input(data: dict[str, Any]) -> ExpenseGroup:
    """
    Validate raw JSON input and return a typed ExpenseGroup.

    This is the single entry point for all input. It performs exhaustive
    validation and returns either a valid ExpenseGroup or raises ValidationError
    with all collected error messages.

    The validation is **atomic**: if any validation error is found, no
    ExpenseGroup is returned.
    """
    report = ValidationReport()

    if not isinstance(data, dict):
        raise ValidationError("Input must be a JSON object")

    members = _validate_members(data.get("members"), report)
    expenses = _validate_expenses(data.get("expenses"), report, members)
    _validate_consistency(members, expenses, report)

    report.raise_if_errors()

    return ExpenseGroup(members=members, expenses=expenses)


# ── member validation ─────────────────────────────────────────────────────────


def _validate_members(raw: Any, report: ValidationReport) -> tuple[Member, ...]:
    if raw is None:
        report.add("Missing required field: 'members'")
        return ()
    if not isinstance(raw, list):
        report.add("'members' must be a list")
        return ()
    if len(raw) == 0:
        report.add("'members' must contain at least one member")
        return ()
    if len(raw) > MAX_MEMBER_COUNT:
        report.add(f"Too many members ({len(raw)}), maximum is {MAX_MEMBER_COUNT}")
        return ()

    members: list[Member] = []
    seen_ids: set[str] = set()

    for i, item in enumerate(raw):
        prefix = f"members[{i}]"
        if not isinstance(item, dict):
            report.add(f"{prefix}: must be an object")
            continue
        mid = item.get("id")
        if mid is None:
            report.add(f"{prefix}: missing required field 'id'")
            continue
        if not isinstance(mid, str):
            report.add(f"{prefix}.id: must be a string, got {type(mid).__name__}")
            continue
        mid = mid.strip()
        if not mid:
            report.add(f"{prefix}.id: must not be empty")
            continue
        if mid in seen_ids:
            report.add(f"{prefix}.id: duplicate member ID '{mid}'")
            continue
        seen_ids.add(mid)

        name = item.get("name")
        if name is not None and not isinstance(name, str):
            report.add(f"{prefix}.name: must be a string, got {type(name).__name__}")
            name = None

        members.append(Member(id=mid, name=name))

    return tuple(members)


# ── expense validation ────────────────────────────────────────────────────────


def _validate_expenses(
    raw: Any, report: ValidationReport, members: tuple[Member, ...]
) -> tuple[Expense, ...]:
    if raw is None:
        report.add("Missing required field: 'expenses'")
        return ()
    if not isinstance(raw, list):
        report.add("'expenses' must be a list")
        return ()
    if len(raw) > MAX_EXPENSE_COUNT:
        report.add(f"Too many expenses ({len(raw)}), maximum is {MAX_EXPENSE_COUNT}")
        return ()

    member_id_set = frozenset(m.id for m in members)
    expenses: list[Expense] = []
    seen_expense_ids: set[str] = set()

    for i, item in enumerate(raw):
        prefix = f"expenses[{i}]"
        if not isinstance(item, dict):
            report.add(f"{prefix}: must be an object")
            continue

        eid = item.get("expense_id")
        if eid is None:
            report.add(f"{prefix}: missing required field 'expense_id'")
            continue
        if not isinstance(eid, str):
            report.add(f"{prefix}.expense_id: must be a string, got {type(eid).__name__}")
            continue
        eid = eid.strip()
        if not eid:
            report.add(f"{prefix}.expense_id: must not be empty")
            continue
        if eid in seen_expense_ids:
            report.add(f"{prefix}.expense_id: duplicate expense ID '{eid}'")
            continue
        seen_expense_ids.add(eid)

        # description
        desc = item.get("description", "")
        if not isinstance(desc, str):
            report.add(f"{prefix}.description: must be a string, got {type(desc).__name__}")
            desc = ""

        # amount
        amount = _validate_amount(item.get("amount"), prefix, report, eid)
        if amount is None:
            continue  # can't validate further without a valid amount

        # currency
        currency = item.get("currency", DEFAULT_CURRENCY)
        if not isinstance(currency, str):
            report.add(f"{prefix}.currency: must be a string, got {type(currency).__name__}")
            currency = DEFAULT_CURRENCY
        elif currency not in SUPPORTED_CURRENCIES:
            report.add(
                f"{prefix}.currency: unsupported currency '{currency}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
            )
            currency = DEFAULT_CURRENCY

        # payer
        payer_id = item.get("payer")
        if payer_id is None:
            report.add(f"{prefix}: missing required field 'payer'")
            continue
        if not isinstance(payer_id, str):
            report.add(f"{prefix}.payer: must be a string, got {type(payer_id).__name__}")
            continue
        payer_id = payer_id.strip()
        if not payer_id:
            report.add(f"{prefix}.payer: must not be empty")
            continue
        if member_id_set and payer_id not in member_id_set:
            report.add(f"{prefix}.payer: unknown member '{payer_id}'")
            continue

        # participants
        participants = _validate_participants(item.get("participants"), prefix, report, member_id_set, eid)

        # split_type
        split_type_raw = item.get("split_type")
        if split_type_raw is None:
            report.add(f"{prefix}: missing required field 'split_type'")
            continue
        if not isinstance(split_type_raw, str):
            report.add(f"{prefix}.split_type: must be a string, got {type(split_type_raw).__name__}")
            continue
        try:
            split_type = SplitType(split_type_raw.lower())
        except ValueError:
            report.add(
                f"{prefix}.split_type: unsupported split type '{split_type_raw}'. "
                f"Supported: {[s.value for s in SplitType]}"
            )
            continue

        # split_details
        split_details = _validate_split_details(
            item.get("split_details"), split_type, amount, participants, prefix, report, eid
        )
        if split_details is None:
            continue

        # timestamp (optional)
        timestamp = item.get("timestamp")
        if timestamp is not None and not isinstance(timestamp, str):
            report.add(f"{prefix}.timestamp: must be a string, got {type(timestamp).__name__}")
            timestamp = None

        try:
            expenses.append(
                Expense(
                    expense_id=eid,
                    description=desc,
                    amount=amount,
                    currency=currency,
                    payer_id=payer_id,
                    participant_ids=participants,
                    split_type=split_type,
                    split_details=split_details,
                    timestamp=timestamp,
                )
            )
        except ValueError as e:
            report.add(f"{prefix}: {e}")

    return tuple(expenses)


def _validate_amount(value: Any, prefix: str, report: ValidationReport, eid: str) -> Decimal | None:
    """Validate a monetary amount. Returns Decimal or None on error."""
    if value is None:
        report.add(f"[expense_id={eid}] {prefix}: missing required field 'amount'")
        return None
    if isinstance(value, bool):
        report.add(f"[expense_id={eid}] {prefix}.amount: must be a number, got boolean")
        return None
    if not isinstance(value, (int, float, str, Decimal)):
        report.add(f"[expense_id={eid}] {prefix}.amount: must be a number, got {type(value).__name__}")
        return None

    if isinstance(value, float):
        if value != value:  # NaN
            report.add(f"[expense_id={eid}] {prefix}.amount: must be a finite number, got NaN")
            return None
        if value == float('inf') or value == float('-inf'):
            report.add(f"[expense_id={eid}] {prefix}.amount: must be a finite number, got infinity")
            return None

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        report.add(f"[expense_id={eid}] {prefix}.amount: invalid decimal value '{value}'")
        return None

    if amount <= 0:
        report.add(f"[expense_id={eid}] {prefix}.amount: must be positive, got {amount}")
        return None
    if amount > MAX_AMOUNT:
        report.add(f"[expense_id={eid}] {prefix}.amount: exceeds maximum allowed ({MAX_AMOUNT})")
        return None

    # Check precision: no more than 2 decimal places
    rounded = amount.quantize(ROUNDING_PRECISION)
    if rounded != amount:
        report.add(
            f"[expense_id={eid}] {prefix}.amount: too many decimal places (max 2), got {amount}"
        )
        return None

    return amount


def _validate_participants(
    raw: Any, prefix: str, report: ValidationReport, member_id_set: frozenset[str], eid: str
) -> tuple[str, ...]:
    if raw is None:
        report.add(f"[expense_id={eid}] {prefix}: missing required field 'participants'")
        return ()
    if not isinstance(raw, list):
        report.add(f"[expense_id={eid}] {prefix}.participants: must be a list")
        return ()
    if len(raw) == 0:
        report.add(f"[expense_id={eid}] {prefix}.participants: must not be empty")
        return ()

    result: list[str] = []
    seen: set[str] = set()
    for j, pid in enumerate(raw):
        if not isinstance(pid, str):
            report.add(f"[expense_id={eid}] {prefix}.participants[{j}]: must be a string")
            continue
        pid = pid.strip()
        if not pid:
            report.add(f"[expense_id={eid}] {prefix}.participants[{j}]: must not be empty")
            continue
        if pid in seen:
            report.add(f"[expense_id={eid}] {prefix}.participants[{j}]: duplicate participant '{pid}'")
            continue
        seen.add(pid)
        if member_id_set and pid not in member_id_set:
            report.add(f"[expense_id={eid}] {prefix}.participants[{j}]: unknown member '{pid}'")
            continue
        result.append(pid)

    return tuple(result)


def _validate_split_details(
    raw: Any,
    split_type: SplitType,
    amount: Decimal,
    participants: tuple[str, ...],
    prefix: str,
    report: ValidationReport,
    eid: str,
) -> tuple[SplitEntry, ...] | None:
    """Validate split_details based on split type. Returns tuple or None on error."""

    if split_type == SplitType.EQUAL:
        # No split_details needed; if provided, ignore (but validate it's a list if given).
        if raw is not None and not isinstance(raw, list):
            report.add(f"[expense_id={eid}] {prefix}.split_details: must be a list for equal split")
        return ()

    if raw is None:
        report.add(f"[expense_id={eid}] {prefix}: split_details required for '{split_type.value}' split")
        return None
    if not isinstance(raw, list):
        report.add(f"[expense_id={eid}] {prefix}.split_details: must be a list")
        return None
    if len(raw) == 0:
        report.add(f"[expense_id={eid}] {prefix}.split_details: must not be empty for '{split_type.value}' split")
        return None

    participant_set = frozenset(participants)
    entries: list[SplitEntry] = []
    seen_members: set[str] = set()
    total_value = Decimal("0")

    for j, entry in enumerate(raw):
        sp = f"{prefix}.split_details[{j}]"
        if not isinstance(entry, dict):
            report.add(f"[expense_id={eid}] {sp}: must be an object")
            continue

        mid = entry.get("member_id")
        if mid is None:
            report.add(f"[expense_id={eid}] {sp}: missing required field 'member_id'")
            continue
        if not isinstance(mid, str):
            report.add(f"[expense_id={eid}] {sp}.member_id: must be a string")
            continue
        mid = mid.strip()
        if not mid:
            report.add(f"[expense_id={eid}] {sp}.member_id: must not be empty")
            continue
        if mid in seen_members:
            report.add(f"[expense_id={eid}] {sp}.member_id: duplicate member '{mid}' in split_details")
            continue
        seen_members.add(mid)
        if participant_set and mid not in participant_set:
            report.add(f"[expense_id={eid}] {sp}.member_id: '{mid}' is not in participants list")
            continue

        value = entry.get("value")
        if value is None:
            report.add(f"[expense_id={eid}] {sp}: missing required field 'value'")
            continue

        if split_type == SplitType.EXACT:
            v = _validate_amount(value, sp, report, eid)
            if v is not None:
                total_value += v
                entries.append(SplitEntry(member_id=mid, value=v))

        elif split_type == SplitType.PERCENTAGE:
            if isinstance(value, bool):
                report.add(f"[expense_id={eid}] {sp}.value: must be a number, got boolean")
                continue
            if not isinstance(value, (int, float, str, Decimal)):
                report.add(f"[expense_id={eid}] {sp}.value: must be a number, got {type(value).__name__}")
                continue
            if isinstance(value, float):
                if value != value:
                    report.add(f"[expense_id={eid}] {sp}.value: must be finite, got NaN")
                    continue
                if value == float('inf') or value == float('-inf'):
                    report.add(f"[expense_id={eid}] {sp}.value: must be finite, got infinity")
                    continue
            try:
                v = Decimal(str(value))
            except (InvalidOperation, ValueError):
                report.add(f"[expense_id={eid}] {sp}.value: invalid decimal value '{value}'")
                continue
            if v < 0:
                report.add(f"[expense_id={eid}] {sp}.value: percentage must not be negative, got {v}")
                continue
            if v > 100:
                report.add(f"[expense_id={eid}] {sp}.value: percentage must not exceed 100, got {v}")
                continue
            total_value += v
            entries.append(SplitEntry(member_id=mid, value=v))

    if report.has_errors():
        return None

    if split_type == SplitType.EXACT:
        if total_value != amount:
            report.add(
                f"[expense_id={eid}] {prefix}.split_details: exact amounts sum "
                f"({total_value}) does not equal expense total ({amount})"
            )
            return None

    elif split_type == SplitType.PERCENTAGE:
        tolerance = Decimal("0.005")
        if abs(total_value - Decimal("100")) > tolerance:
            report.add(
                f"[expense_id={eid}] {prefix}.split_details: percentages sum to "
                f"{total_value}%, must sum to 100%"
            )
            return None

    return tuple(entries)


def _validate_consistency(
    members: tuple[Member, ...],
    expenses: tuple[Expense, ...],
    report: ValidationReport,
) -> None:
    """Cross-validate members and expenses."""
    # All payers must be members (already checked in per-expense validation
    # if member_id_set is non-empty). This is a secondary consistency check.
    member_ids = frozenset(m.id for m in members)
    for expense in expenses:
        if expense.payer_id not in member_ids:
            report.add(
                f"[expense_id={expense.expense_id}] payer '{expense.payer_id}' "
                f"is not a group member"
            )
        for pid in expense.participant_ids:
            if pid not in member_ids:
                report.add(
                    f"[expense_id={expense.expense_id}] participant '{pid}' "
                    f"is not a group member"
                )


def validate_file_size(filepath: str) -> None:
    """Validate that the input file exists and is within size limits."""
    import os
    if not os.path.isfile(filepath):
        raise ValidationError(f"File not found: {filepath}")
    size = os.path.getsize(filepath)
    if size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File too large: {size} bytes (maximum {MAX_FILE_SIZE_BYTES} bytes)"
        )
    if size == 0:
        raise ValidationError("File is empty")