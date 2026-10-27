"""Core SLA computation (M3, M4).

For each ticket:
  M3 – Extract *active* periods (status ≠ ON_HOLD) from the status history.
  M4 – Compute: elapsed business minutes, due-by, breach flag, breach minutes.
"""

from __future__ import annotations

from datetime import date, datetime, time

from .calendar import add_business_minutes, business_minutes_between
from .models import SlaPolicy, Ticket, TicketSlaResult

# ---------------------------------------------------------------------------
# active-period extraction (M3)
# ---------------------------------------------------------------------------


def _active_periods(
    ticket: Ticket,
    reference_time: datetime,
) -> list[tuple[datetime, datetime]]:
    """Return a list of (start, end) intervals where the SLA clock ran.

    'reference_time' is treated as the end of the analysis window
    (either the resolved time or 'now' for unresolved tickets).
    """
    history = sorted(ticket.status_history, key=lambda e: e.at)

    if not history:
        # No status history → the whole window is active.
        return [(ticket.created, reference_time)]

    periods: list[tuple[datetime, datetime]] = []

    # Walk consecutive pairs in the history.
    for i in range(len(history)):
        seg_start = history[i].at
        seg_end = history[i + 1].at if i + 1 < len(history) else reference_time

        if seg_end <= seg_start:
            continue

        # The status *at* seg_start determines whether the clock runs for
        # this segment.  "ON_HOLD" is the only status that pauses the clock.
        if history[i].status.upper() != "ON_HOLD":
            periods.append((seg_start, seg_end))

    return periods


# ---------------------------------------------------------------------------
# per-ticket SLA result (M4)
# ---------------------------------------------------------------------------

def _parse_time(t: str) -> time:
    """Parse 'HH:MM' → time object."""
    return time.fromisoformat(t)


def compute_ticket_sla(
    ticket: Ticket,
    policy: SlaPolicy,
    holidays: set[date],
    reference_time: datetime | None = None,
) -> TicketSlaResult | None:
    """Compute the SLA result for a single ticket.

    Returns None when the ticket priority has no target defined.
    """
    target_minutes = policy.targets.get(ticket.priority.upper())
    if target_minutes is None:
        return None

    ref = reference_time or datetime.now().replace(microsecond=0)

    # A resolved ticket stops the SLA clock at its resolved time.  An open
    # ticket runs until the reference time (default: now).
    window_end = ticket.resolved if ticket.resolved is not None else ref

    # ---- M3: isolate active periods -----------------------------------------
    active = _active_periods(ticket, window_end)

    # ---- M4: sum business minutes over active periods ------------------------
    elapsed = 0
    for s, e in active:
        elapsed += business_minutes_between(
            s,
            e,
            holidays,
            business_start=_parse_time(policy.business_start),
            business_end=_parse_time(policy.business_end),
        )

    # ---- M4: due-by (forward projection) ------------------------------------
    due_by = add_business_minutes(
        ticket.created,
        target_minutes,
        holidays,
        business_start=_parse_time(policy.business_start),
        business_end=_parse_time(policy.business_end),
    )

    breached = elapsed > target_minutes
    breach_minutes = max(0, elapsed - target_minutes)

    return TicketSlaResult(
        ticket_id=ticket.id,
        priority=ticket.priority,
        assignee_group=ticket.assignee_group,
        elapsed_business_minutes=elapsed,
        target_minutes=target_minutes,
        due_by=due_by,
        breached=breached,
        breach_minutes=breach_minutes,
    )


# ---------------------------------------------------------------------------
# batch computation
# ---------------------------------------------------------------------------


def compute_all_tickets(
    tickets: list[Ticket],
    policy: SlaPolicy,
    holidays: set[date],
    reference_time: datetime | None = None,
) -> list[TicketSlaResult]:
    """Compute SLA results for every ticket; tickets with unknown priorities
    are skipped with a warning printed to stderr."""
    results: list[TicketSlaResult] = []
    for ticket in tickets:
        res = compute_ticket_sla(ticket, policy, holidays, reference_time)
        if res is None:
            import sys

            print(
                f"WARNING: skipping ticket {ticket.id} — "
                f"unknown priority '{ticket.priority}'",
                file=sys.stderr,
            )
            continue
        results.append(res)
    return results