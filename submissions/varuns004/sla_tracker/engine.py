"""SLA evaluation: turns a ticket's status history into SLA metrics."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .business_calendar import BusinessCalendar
from .models import INITIAL_STATUS, PAUSED, RUNNING, STOPPED, SlaPolicy, Ticket, TicketResult

Segment = tuple[datetime, datetime, str]


def build_segments(ticket: Ticket, as_of: datetime) -> list[Segment]:
    """Split [created_at, as_of] into contiguous (start, end, status) segments.

    History must be sorted (the loader guarantees this). Events after
    ``as_of`` are ignored, enabling point-in-time ("as of") replays.
    """
    status, seg_start = INITIAL_STATUS, ticket.created_at
    segments: list[Segment] = []
    for event in ticket.history:
        if event.at > as_of:
            break
        segments.append((seg_start, event.at, status))
        status, seg_start = event.status, event.at
    segments.append((seg_start, as_of, status))
    return segments


def evaluate_ticket(
    ticket: Ticket, policy: SlaPolicy, calendar: BusinessCalendar, as_of: datetime
) -> TicketResult:
    segments = build_segments(ticket, as_of)
    target = policy.targets_minutes[ticket.priority] * 60
    elapsed = paused = 0
    remaining = target
    due_by: datetime | None = None

    for start, end, status in segments:
        state = policy.classify(status)
        seconds = calendar.business_seconds(start, end)
        if state == RUNNING:
            if due_by is None:
                if remaining <= seconds:
                    due_by = calendar.add_business_seconds(start, remaining)
                else:
                    remaining -= seconds
            elapsed += seconds
        elif state == PAUSED:
            paused += seconds

    last_start, _, current_status = segments[-1]
    clock_state = policy.classify(current_status)
    if due_by is None:
        # Target not yet consumed: project forward from where the clock stands
        # (resolution time if stopped, otherwise as_of), assuming no new holds.
        clock_end = last_start if clock_state == STOPPED else as_of
        due_by = calendar.add_business_seconds(clock_end, remaining)

    at_risk = (
        clock_state != STOPPED
        and elapsed <= target
        and elapsed >= policy.at_risk_ratio * target
    )
    return TicketResult(
        ticket_id=ticket.ticket_id,
        priority=ticket.priority,
        assignee_group=ticket.assignee_group,
        current_status=current_status,
        clock_state=clock_state,
        target_seconds=target,
        elapsed_seconds=elapsed,
        paused_seconds=paused,
        due_by=due_by,
        at_risk=at_risk,
    )


def evaluate_all(
    tickets: Iterable[Ticket], policy: SlaPolicy, calendar: BusinessCalendar, as_of: datetime
) -> list[TicketResult]:
    return [evaluate_ticket(t, policy, calendar, as_of) for t in tickets]

