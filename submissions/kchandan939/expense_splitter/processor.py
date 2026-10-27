"""Orchestrator — parse, validate, compute, simplify, report."""

from __future__ import annotations

from typing import Any, Dict, List

from .balance import compute_balances
from .models import Expense, SplitResult
from .simplify import simplify
from .validation import _parse_expense, validate_expense_full


def process(expenses: List[Dict[str, Any]]) -> SplitResult:
    """Run the full pipeline on a list of raw expense dicts.

    Invalid expenses (hard errors) are skipped with an error logged.
    Soft warnings (e.g. missing participant defaults) are logged but
    the expense is still processed.
    """
    errors: List[str] = []
    warnings: List[str] = []
    valid: List[Expense] = []

    if not isinstance(expenses, list):
        return SplitResult(
            balances={}, settlements=[], errors=["input must be a JSON array"]
        )

    for i, raw in enumerate(expenses):
        if not isinstance(raw, dict):
            errors.append(f"[{i}] not a JSON object; skipped")
            continue
        try:
            exp = _parse_expense(raw)
        except (TypeError, ValueError) as exc:
            errors.append(f"[{i}] parse error: {exc}")
            continue
        hard, soft = validate_expense_full(exp)
        if hard:
            errors.append(f"[{i}] '{exp.description}': {hard}")
            continue
        if soft:
            warnings.append(f"[{i}] '{exp.description}': {soft}")
        valid.append(exp)

    if not valid:
        return SplitResult(
            balances={},
            settlements=[],
            errors=errors + warnings + ["no valid expenses to process"],
        )

    balances = compute_balances(valid)
    settlements = simplify(balances)

    return SplitResult(
        balances=balances,
        settlements=settlements,
        expenses_processed=len(valid),
        errors=errors + warnings,
    )