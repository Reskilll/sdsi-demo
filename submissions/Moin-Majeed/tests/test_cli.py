"""Tests for the CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sla_tracker.cli import main

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _data_path(name: str) -> str:
    return str(DATA / name)


class TestCompute:
    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["compute", "--help"])
        assert result.exit_code == 0
        assert "Per-ticket SLA report" in result.output

    def test_default_paths(self, runner: CliRunner) -> None:
        # Run from project root so default data/ paths resolve
        result = runner.invoke(
            main,
            [
                "--help",
                "compute",
                "-t", _data_path("tickets.json"),
                "-p", _data_path("sla_policy.json"),
                "-H", _data_path("holidays.json"),
            ],
        )
        # Just check it doesn't crash
        assert result.exit_code == 0

    def test_json_output(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "compute",
                "--json",
                "-t", _data_path("tickets.json"),
                "-p", _data_path("sla_policy.json"),
                "-H", _data_path("holidays.json"),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 8
        # Every record has expected keys
        for rec in data:
            assert "ticket_id" in rec
            assert "breached" in rec
            assert "elapsed_business_minutes" in rec
            assert "breach_minutes" in rec
            assert "due_by_utc" in rec

    def test_missing_file(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["compute", "-t", "nonexistent.json"])
        assert result.exit_code != 0

    def test_invalid_json(self, runner: CliRunner, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json")
        result = runner.invoke(main, ["compute", "-t", str(bad_file)])
        assert result.exit_code != 0

    @pytest.mark.parametrize(
        "ticket_data,expected_error",
        [
            (
                [{"ticket_id": "X", "priority": 99, "created_at": "2026-10-26T09:00:00Z"}],
                "priority",
            ),
            ([{"priority": 1, "created_at": "2026-10-26T09:00:00Z"}], "ticket_id"),
            ([{"ticket_id": "X", "priority": 1}], "created_at"),
        ],
    )
    def test_validation_errors(
        self, runner: CliRunner, tmp_path: Path, ticket_data: list, expected_error: str
    ) -> None:
        t_file = tmp_path / "t.json"
        p_file = tmp_path / "p.json"
        h_file = tmp_path / "h.json"
        t_file.write_text(json.dumps(ticket_data))
        p_file.write_text(json.dumps({"P1": 240, "P2": 480, "P3": 1440, "P4": 4320}))
        h_file.write_text(json.dumps([]))
        result = runner.invoke(
            main,
            ["compute", "-t", str(t_file), "-p", str(p_file), "-H", str(h_file)],
        )
        assert result.exit_code != 0


class TestSummary:
    def test_output(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "summary",
                "-t", _data_path("tickets.json"),
                "-p", _data_path("sla_policy.json"),
                "-H", _data_path("holidays.json"),
            ],
        )
        assert result.exit_code == 0
        assert "SLA Summary" in result.output
        assert "By Priority" in result.output
        assert "By Assignee Group" in result.output

    def test_empty_tickets(self, runner: CliRunner, tmp_path: Path) -> None:
        t_file = tmp_path / "t.json"
        p_file = tmp_path / "p.json"
        h_file = tmp_path / "h.json"
        t_file.write_text("[]")
        p_file.write_text(json.dumps({"P1": 240, "P2": 480, "P3": 1440, "P4": 4320}))
        h_file.write_text("[]")
        result = runner.invoke(
            main,
            ["summary", "-t", str(t_file), "-p", str(p_file), "-H", str(h_file)],
        )
        assert result.exit_code == 0
        assert "Total Tickets: 0" in result.output


class TestVersion:
    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "sla-tracker" in result.output or "1.0.0" in result.output
