"""Integration tests — run the full pipeline via CLI on sample files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).resolve().parent.parent
SINGLE = SAMPLES_DIR / "sample_expenses.json"
BATCH = SAMPLES_DIR / "sample_batch.json"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "expense_splitter", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(SAMPLES_DIR),
    )


class TestCLIIntegration:
    def test_single_group_pretty_output(self):
        result = run_cli(str(SINGLE))
        assert result.returncode == 0, result.stderr
        assert "Goa Trip 2026" in result.stdout
        assert "NET BALANCES" in result.stdout
        assert "SIMPLIFIED SETTLEMENTS" in result.stdout

    def test_single_group_json_output(self):
        result = run_cli(str(SINGLE), "--json")
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert data[0]["group"] == "Goa Trip 2026"
        assert data[0]["balances"] is not None
        assert len(data[0]["settlements"]) > 0

    def test_batch_json_output(self):
        result = run_cli(str(BATCH), "--json")
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert len(data) == 2
        assert {g["group"] for g in data} == {"Weekend Brunch", "Office Diwali Party"}

    def test_batch_pretty_output(self):
        result = run_cli(str(BATCH))
        assert result.returncode == 0, result.stderr
        assert "Weekend Brunch" in result.stdout
        assert "Office Diwali Party" in result.stdout

    def test_file_not_found_exits_1(self):
        result = run_cli("nonexistent.json")
        assert result.returncode == 1

    def test_invalid_json_exits_1(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        result = run_cli(str(bad_file))
        assert result.returncode == 1

    def test_validation_errors_exit_1(self, tmp_path):
        """A file with invalid data should exit 1 and report errors."""
        bad_data = {
            "group": "Bad Group",
            "members": ["A", "B"],
            "expenses": [
                {
                    "description": "Bad expense",
                    "total": 100,
                    "paid_by": "Z",  # not a member
                    "split_type": "equal",
                    "members": ["A", "B"],
                }
            ],
        }
        bad_file = tmp_path / "bad_group.json"
        bad_file.write_text(json.dumps(bad_data))
        result = run_cli(str(bad_file))
        assert result.returncode == 1, result.stdout
        assert "VALIDATION ERRORS" in result.stdout or "Z" in result.stdout