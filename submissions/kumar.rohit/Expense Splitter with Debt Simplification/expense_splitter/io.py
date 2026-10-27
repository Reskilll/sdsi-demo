"""
JSON input/output – read expense data from JSON files and format results.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .exceptions import ValidationError
from .models import ExpenseGroup, ExpenseResult, MemberBalance, Settlement
from .validation import validate_file_size, validate_input


def read_expenses(filepath: str | Path) -> ExpenseGroup:
    """
    Read and validate expense data from a JSON file.

    Args:
        filepath: Path to the JSON input file.

    Returns:
        A validated ExpenseGroup.

    Raises:
        ValidationError: If the file cannot be read, is malformed, or fails validation.
        OSError: For filesystem errors.
    """
    filepath = Path(filepath)
    validate_file_size(str(filepath))

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {filepath}: {e}") from e
    except OSError as e:
        raise ValidationError(f"Cannot read file {filepath}: {e}") from e

    if not isinstance(data, dict):
        raise ValidationError("Top-level JSON must be an object, not an array")

    return validate_input(data)


def result_to_dict(result: ExpenseResult) -> dict[str, Any]:
    """Convert an ExpenseResult to a JSON-serializable dictionary."""
    return {
        "summary": {
            "member_count": result.member_count,
            "expense_count": result.expense_count,
        },
        "balances": [
            {
                "member_id": b.member_id,
                "total_paid": str(b.total_paid),
                "total_share": str(b.total_share),
                "net_balance": str(b.net_balance),
            }
            for b in result.balances
        ],
        "settlements": [
            {
                "from": s.from_member_id,
                "to": s.to_member_id,
                "amount": str(s.amount),
            }
            for s in result.settlements
        ],
        "errors": list(result.errors) if result.errors else [],
    }


def format_human_readable(result: ExpenseResult) -> str:
    """Format an ExpenseResult for human-readable terminal output."""
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  EXPENSE SPLITTER – RESULTS")
    lines.append("=" * 60)

    if result.errors:
        lines.append("\n⚠ ERRORS:")
        for e in result.errors:
            lines.append(f"  - {e}")
        return "\n".join(lines)

    lines.append(f"\nProcessed: {result.expense_count} expense(s) across {result.member_count} member(s)")

    # Balances
    lines.append("\n" + "-" * 40)
    lines.append("  BALANCES")
    lines.append("-" * 40)
    if not result.balances:
        lines.append("  (none)")
    else:
        header = f"  {'Member':<20} {'Paid':>10} {'Share':>10} {'Net':>10}"
        lines.append(header)
        lines.append("  " + "-" * len(header.lstrip()))
        for b in result.balances:
            net_str = f"{b.net_balance:+.2f}"
            lines.append(
                f"  {b.member_id:<20} {b.total_paid:>10.2f} {b.total_share:>10.2f} {net_str:>10}"
            )

    # Settlements
    lines.append("\n" + "-" * 40)
    lines.append("  SETTLEMENTS")
    lines.append("-" * 40)
    if not result.settlements:
        lines.append("  No settlements needed – everyone is settled!")
    else:
        for s in result.settlements:
            lines.append(f"  {s.from_member_id} pays {s.to_member_id} ₹{s.amount:.2f}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def format_json_output(result: ExpenseResult) -> str:
    """Format an ExpenseResult as pretty-printed JSON."""
    return json.dumps(result_to_dict(result), indent=2, ensure_ascii=False)


def write_output(result: ExpenseResult, filepath: str | Path | None, json_mode: bool = False) -> str:
    """
    Format and optionally write the result to a file.

    Returns the formatted output string.
    """
    if json_mode:
        output = format_json_output(result)
    else:
        output = format_human_readable(result)

    if filepath:
        filepath = Path(filepath)
        if filepath.exists():
            raise ValidationError(f"Output file already exists: {filepath}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)

    return output