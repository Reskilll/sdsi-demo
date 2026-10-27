"""Command-line interface for the SLA tracker.

Supports two subcommands:

    sla-tracker compute    Per-ticket SLA report
    sla-tracker summary    Aggregate breach summary

Both accept ``--tickets``, ``--policy``, ``--holidays`` flags, plus an
optional ``--tz`` for configuring the business-hours timezone.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import click

from sla_tracker.business_calendar import BusinessCalendar
from sla_tracker.models import SlaPolicy, Ticket
from sla_tracker.reporter import (
    build_summary,
    format_summary,
    format_ticket_report,
)
from sla_tracker.sla_calculator import calculate_ticket_sla
from sla_tracker.validators import (
    ValidationError,
    validate_holidays,
    validate_sla_policy,
    validate_ticket,
)

_EXIT_OK = 0
_EXIT_ERR = 1


def _load_json(path: Path) -> object:
    """Load and parse a JSON file, with clear error messages."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in {path}: {exc}") from exc
    except FileNotFoundError as exc:
        raise click.ClickException(f"File not found: {path}") from exc


# ── shared options ───────────────────────────────────────────────────────────

def _common_options(f):
    """Decorator that adds shared CLI options."""
    options = [
        click.option(
            "--tickets", "-t",
            type=click.Path(exists=True, path_type=Path),
            default=Path("data/tickets.json"),
            show_default=True,
            help="Path to tickets JSON file.",
        ),
        click.option(
            "--policy", "-p",
            type=click.Path(exists=True, path_type=Path),
            default=Path("data/sla_policy.json"),
            show_default=True,
            help="Path to SLA policy JSON file.",
        ),
        click.option(
            "--holidays", "-H",
            type=click.Path(exists=True, path_type=Path),
            default=Path("data/holidays.json"),
            show_default=True,
            help="Path to holidays JSON file.",
        ),
        click.option(
            "--tz",
            default="UTC",
            show_default=True,
            help="IANA timezone for the support centre (e.g. 'America/New_York').",
        ),
    ]
    for opt in reversed(options):
        f = opt(f)
    return f


# ── subcommands ──────────────────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="sla-tracker")
def main() -> None:
    """IT Service-Desk SLA Tracker — compute SLA breaches for support tickets."""


@main.command("compute")
@_common_options
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output report as JSON instead of human-readable text.",
)
def compute_cmd(
    tickets: Path,
    policy: Path,
    holidays: Path,
    tz: str,
    output_json: bool,
) -> None:
    """Per-ticket SLA report with breach status."""
    reports = _run_computation(tickets, policy, holidays, tz)

    if output_json:
        _emit_json(_reports_to_json(reports), tickets)
    else:
        for report in reports:
            click.echo(format_ticket_report(report))
            click.echo("")


@main.command("summary")
@_common_options
def summary_cmd(
    tickets: Path,
    policy: Path,
    holidays: Path,
    tz: str,
) -> None:
    """Aggregate SLA breach summary by priority and assignee group."""
    reports = _run_computation(tickets, policy, holidays, tz)
    summary = build_summary(reports)
    click.echo(format_summary(summary))


# ── core pipeline ────────────────────────────────────────────────────────────


def _run_computation(
    tickets_path: Path,
    policy_path: Path,
    holidays_path: Path,
    tz: str,
) -> list:
    """Load, validate, and compute SLA reports for all tickets.

    Returns a list of ``TicketReport`` objects.
    """
    # Load raw JSON
    raw_tickets = _load_json(tickets_path)
    raw_policy = _load_json(policy_path)
    raw_holidays = _load_json(holidays_path)

    # Validate
    try:
        holiday_set: set[date] = validate_holidays(raw_holidays)  # type: ignore[arg-type]
        targets = validate_sla_policy(raw_policy)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise click.ClickException(str(exc)) from exc

    sla_policy = SlaPolicy(targets=targets)
    calendar = BusinessCalendar(holidays=holiday_set, tz=tz)

    if not isinstance(raw_tickets, list):
        raise click.ClickException("Tickets file must contain a JSON array of ticket objects")

    validated_tickets: list[Ticket] = []
    errors: list[str] = []
    for i, raw_tkt in enumerate(raw_tickets):
        try:
            validated_tickets.append(validate_ticket(raw_tkt))
        except ValidationError as exc:
            errors.append(f"Ticket[{i}]: {exc}")

    if errors:
        for err in errors:
            click.echo(f"Error: {err}", err=True)
        raise click.ClickException(f"{len(errors)} ticket(s) failed validation. See above.")

    # Compute

    now = datetime.now(tz=timezone.utc)
    reports = [
        calculate_ticket_sla(ticket=t, sla_policy=sla_policy, calendar=calendar, ref=now)
        for t in validated_tickets
    ]
    return reports


# ── JSON serialisation ───────────────────────────────────────────────────────


def _reports_to_json(reports: list) -> list[dict]:
    """Convert reports to a JSON-serialisable list of dicts."""
    result = []
    for r in reports:
        rec = {
            "ticket_id": r.ticket_id,
            "priority": f"P{r.priority.value}",
            "assignee_group": r.assignee_group,
            "elapsed_business_minutes": round(r.elapsed_business_minutes, 1),
            "sla_target_minutes": r.sla_target_minutes,
            "due_by_utc": r.due_by.isoformat(),
            "breached": r.breached,
            "breach_minutes": round(r.breach_minutes, 1),
        }
        result.append(rec)
    return result


def _emit_json(data: list[dict], source_path: Path) -> None:
    """Print JSON to stdout."""
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


# Allow running as ``python -m sla_tracker.cli``
if __name__ == "__main__":
    main()
