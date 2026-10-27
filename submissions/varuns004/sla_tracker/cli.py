"""Command-line entry point.

Exit codes: 0 success, 1 breaches found with --fail-on-breach,
2 invalid input/configuration (or rejected tickets with --strict).
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import __version__
from .business_calendar import BusinessCalendar
from .engine import evaluate_all
from .loader import load_holidays, load_policy, load_tickets
from .models import ConfigError, SlaError
from .report import RENDERERS, build_report
from .timeutil import parse_timestamp

EXIT_OK, EXIT_BREACH, EXIT_INPUT = 0, 1, 2
log = logging.getLogger("sla_tracker")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sla_tracker",
        description="Compute business-hours SLA breaches for IT service-desk tickets.",
    )
    p.add_argument("--tickets", required=True, help="path to tickets JSON")
    p.add_argument("--policy", required=True, help="path to SLA policy JSON")
    p.add_argument("--holidays", help="path to holidays JSON (optional)")
    p.add_argument("--as-of", help="evaluation time, ISO-8601 (default: now)")
    p.add_argument("--format", choices=sorted(RENDERERS), default="table")
    p.add_argument("--output", help="write report to this file instead of stdout")
    p.add_argument("--fail-on-breach", action="store_true", help="exit 1 if any ticket breached")
    p.add_argument("--strict", action="store_true", help="exit 2 if any ticket is rejected")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging to stderr")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def run(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    calendar = BusinessCalendar(
        policy.day_start, policy.day_end, policy.working_days, load_holidays(args.holidays)
    )
    try:
        as_of = (
            parse_timestamp(args.as_of, policy.timezone, "--as-of")
            if args.as_of
            else parse_timestamp(datetime.now(timezone.utc).isoformat(), policy.timezone, "now")
        )
    except ValueError as exc:
        raise ConfigError(str(exc)) from None

    tickets, errors = load_tickets(args.tickets, policy, as_of)
    log.debug("loaded %d tickets, rejected %d", len(tickets), len(errors))
    results = evaluate_all(tickets, policy, calendar, as_of)
    report = build_report(results, errors, policy, as_of)
    text = RENDERERS[args.format](report)

    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8", newline="")
        except OSError:
            raise ConfigError("could not write the output file") from None
    else:
        sys.stdout.write(text)

    for err in errors:
        print(f"warning: rejected ticket {err.ticket_ref}: {err.message}", file=sys.stderr)
    if args.strict and errors:
        return EXIT_INPUT
    if args.fail_on_breach and any(r.breached for r in results):
        return EXIT_BREACH
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s: %(message)s")
    try:
        return run(args)
    except SlaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except Exception:  # last-resort guard: never dump a stack trace by default
        log.debug("unexpected failure", exc_info=True)
        print("error: unexpected internal error (re-run with -v for details)", file=sys.stderr)
        return EXIT_INPUT

