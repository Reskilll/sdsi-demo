"""
JSON Processor — batch and single-file ingestion for M4.

Supports:
- Single .json file:  process_one()
- Directory of .json files: process_batch()
- stdin pipe: process_stdin()

Security guards (unlisted edge cases):
- File size limit: 50 MiB per file (prevents DoS via giant uploads)
- Member name: max 100 chars, no control characters
- Max members: 10,000  (prevents heap exhaustion)
- Max expenses: 100,000 (prevents OOM in balance computation)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.errors import BatchError, InputFormatError, SplitwiseError
from src.models.split import validate_amount
from src.services.group_manager import GroupManager

# ---------------------------------------------------------------------------
# Security limits
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024        # 50 MiB
MAX_MEMBER_NAME_LENGTH = 100                   # characters
MAX_MEMBERS = 10_000                           # per group
MAX_EXPENSES = 100_000                         # per group
MAX_DESCRIPTION_LENGTH = 500                   # per expense

# Control-character pattern for member name validation.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


@dataclass
class ProcessResult:
    """The outcome of processing one JSON input."""
    file_path: str
    group: GroupManager | None
    summary: dict | None
    error: SplitwiseError | None


class JSONProcessor:
    """Turn JSON payloads into GroupManager instances."""

    @staticmethod
    def _build_group(data: dict, file_path: str = "<input>") -> GroupManager:
        """Construct a GroupManager from a validated JSON dict.

        Raises InputFormatError or MemberNotFoundError for bad data.
        """
        group_data = data.get("group")
        if not isinstance(group_data, dict):
            raise InputFormatError(f"{file_path}: missing or invalid 'group' object")

        group_name = group_data.get("name", "")
        if not isinstance(group_name, str):
            group_name = ""
        if len(group_name) > 200:
            raise InputFormatError(f"{file_path}: group name exceeds 200 characters")

        member_names = group_data.get("members")
        if not isinstance(member_names, list) or len(member_names) < 1:
            raise InputFormatError(
                f"{file_path}: 'group.members' must be a list with at least 1 member"
            )
        if len(member_names) > MAX_MEMBERS:
            raise InputFormatError(
                f"{file_path}: group has {len(member_names)} members; max is {MAX_MEMBERS}"
            )

        seen: set[str] = set()
        for name in member_names:
            if not isinstance(name, str) or not name.strip():
                raise InputFormatError(
                    f"{file_path}: member name must be a non-empty string, got {name!r}"
                )
            # Security: deny control characters and overlength names.
            if _CONTROL_RE.search(name):
                raise InputFormatError(
                    f"{file_path}: member name {name!r} contains control characters"
                )
            if len(name) > MAX_MEMBER_NAME_LENGTH:
                raise InputFormatError(
                    f"{file_path}: member name exceeds {MAX_MEMBER_NAME_LENGTH} characters"
                )
            if name in seen:
                raise InputFormatError(f"{file_path}: duplicate member name '{name}'")
            seen.add(name)

        gm = GroupManager(group_name)
        for name in member_names:
            gm.add_member(name)

        expenses_data = data.get("expenses")
        if expenses_data is None:
            return gm

        if not isinstance(expenses_data, list):
            raise InputFormatError(f"{file_path}: 'expenses' must be a list")

        if len(expenses_data) > MAX_EXPENSES:
            raise InputFormatError(
                f"{file_path}: {len(expenses_data)} expenses; max is {MAX_EXPENSES}"
            )

        for i, exp_data in enumerate(expenses_data):
            if not isinstance(exp_data, dict):
                raise InputFormatError(f"{file_path}: expense[{i}] must be an object")
            _add_expense_from_dict(gm, exp_data, file_path, i)

        return gm

    @staticmethod
    def process_one(file_path: str) -> dict:
        """Process a single JSON file and return the summary dict."""
        path = Path(file_path)
        if not path.exists():
            raise InputFormatError(f"File not found: {file_path}")

        # Security: reject oversized files.
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise InputFormatError(
                f"{file_path}: file size {file_size} bytes exceeds limit "
                f"of {MAX_FILE_SIZE_BYTES} bytes"
            )

        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise InputFormatError(f"{file_path}: invalid JSON — {exc}") from exc

        if not isinstance(data, dict):
            raise InputFormatError(f"{file_path}: top-level JSON must be an object")

        gm = JSONProcessor._build_group(data, file_path)
        return gm.summary()

    @staticmethod
    def process_batch(directory: str) -> list[dict]:
        """Process all .json files in a directory.  Errors collected, not skipped."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise InputFormatError(f"Not a directory: {directory}")

        json_files = sorted(dir_path.glob("*.json"))
        if not json_files:
            raise InputFormatError(f"No .json files found in {directory}")

        results: list[dict] = []
        for jf in json_files:
            try:
                summary = JSONProcessor.process_one(str(jf))
                results.append({"file": str(jf), "result": summary})
            except SplitwiseError as exc:
                results.append({"file": str(jf), "error": str(exc)})

        return results

    @staticmethod
    def process_stdin() -> dict:
        """Read JSON from stdin and return summary."""
        raw = sys.stdin.read()
        if not raw.strip():
            raise InputFormatError("stdin is empty")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InputFormatError(f"stdin: invalid JSON — {exc}") from exc
        if not isinstance(data, dict):
            raise InputFormatError("stdin: top-level JSON must be an object")
        gm = JSONProcessor._build_group(data, "<stdin>")
        return gm.summary()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _add_expense_from_dict(
    gm: GroupManager,
    exp_data: dict,
    file_path: str,
    index: int,
) -> None:
    """Validate and add a single expense from the JSON dict."""
    prefix = f"{file_path}: expense[{index}]"

    description = exp_data.get("description", "")
    if not isinstance(description, str) or not description.strip():
        raise InputFormatError(f"{prefix}: 'description' must be a non-empty string")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise InputFormatError(
            f"{prefix}: description exceeds {MAX_DESCRIPTION_LENGTH} characters"
        )

    payer_name = exp_data.get("payer")
    if not isinstance(payer_name, str) or not payer_name.strip():
        raise InputFormatError(f"{prefix}: 'payer' must be a non-empty string")

    raw_amount = exp_data.get("amount")
    if raw_amount is None:
        raise InputFormatError(f"{prefix}: 'amount' is required")

    amount = validate_amount(raw_amount)

    split_data = exp_data.get("split")
    if not isinstance(split_data, dict):
        raise InputFormatError(f"{prefix}: 'split' object is required")

    gm.add_expense(
        description=description,
        payer_name=payer_name,
        amount=amount,
        split_data=split_data,
    )