"""Agent — the main entry point. Orchestrates the full triage pipeline."""

from __future__ import annotations

from typing import Optional

from classifier import Classifier
from config import CATEGORY_ROUTING, CONFIDENCE_THRESHOLD
from drafter import Drafter
from logger import ActionLogger
from models import (
    ActionLog,
    ActionType,
    DraftResponse,
    Ticket,
    TicketCategory,
    TriageResult,
)
from pipeliner import TriagePipeline


def run(task: str, logger: Optional[ActionLogger] = None) -> TriageResult:
    """Entry point matching the agent-template signature.

    Args:
        task: The ticket content. If JSON, parsed as Ticket fields;
              otherwise treated as raw body text and wrapped.
        logger: Optional pre-configured logger; created if omitted.

    Returns:
        TriageResult with classification, routing, draft, and action log.
    """
    import json

    if logger is None:
        logger = ActionLogger()

    # ---- Parse input --------------------------------------------------------
    ticket = _parse_task(task, logger)

    # ---- Run pipeline -------------------------------------------------------
    pipeline = TriagePipeline(logger=logger)
    result = pipeline.run(ticket)

    return result


def run_batch(
    tasks: list[str],
    logger: Optional[ActionLogger] = None,
) -> list[TriageResult]:
    """Process multiple tickets sequentially.

    Args:
        tasks: List of ticket strings (JSON or plain text).
        logger: Optional logger shared across all tickets.

    Returns:
        List of TriageResult, one per ticket.
    """
    if logger is None:
        logger = ActionLogger()

    results: list[TriageResult] = []
    for task in tasks:
        results.append(run(task, logger=logger))
    return results


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _parse_task(task: str, logger: ActionLogger) -> Ticket:
    """Try JSON parse first; fall back to treating string as body."""
    import json

    try:
        data = json.loads(task)
        ticket = Ticket(**data)
    except (json.JSONDecodeError, TypeError):
        # Treat as plain body text with a generated subject
        ticket = Ticket(
            ticket_id=f"AUTO-{hash(task) % 10_000:04d}",
            subject=task[:80].replace("\n", " ").strip() + ("..." if len(task) > 80 else ""),
            body=task,
            sender_email="unknown@example.com",
        )

    _log_event(logger, ticket.ticket_id, ActionType.CLASSIFY, "started")
    return ticket


def _log_event(
    logger: ActionLogger,
    ticket_id: str,
    action: ActionType,
    message: str,
    **extra: object,
) -> None:
    logger.log(ActionLog(
        ticket_id=ticket_id,
        action=action,
        detail={"message": message, **extra},
    ))