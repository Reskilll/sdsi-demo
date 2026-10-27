"""Core SLA computation engine.

Coordinates the business calendar, ticket status timeline, and SLA policy to
produce per-ticket breach reports.

Edge cases handled:
- Ticket created outside business hours → clock starts at next business open.
- Ticket created on a holiday/weekend → clock starts at next business day.
- ON_HOLD segments pause the clock; clock resumes at the *next business minute*
  after the ON_HOLD ends (e.g. if ON_HOLD ends at 10:30, the clock resumes at
  10:30 the same or next business day).
- A ticket that never leaves ON_HOLD has its clock stopped; a ticket that is
  never resolved contributes time up to "now" (or the last status timestamp).
- If a ticket has no status_history, a single OPEN at created_at is implied.
- Multiple ON_HOLD segments are handled independently.
- Overlapping or empty intervals in the status timeline are safe (the clock
  counts only positive, non-overlapping segments).
"""

from __future__ import annotations

from datetime import datetime

from sla_tracker.business_calendar import BusinessCalendar
from sla_tracker.models import (
    SlaPolicy,
    Ticket,
    TicketReport,
    TicketStatus,
)

# ── "now" sentinel: use the last status timestamp ────────────────────────────

def _effective_end(ticket: Ticket, ref: datetime | None) -> datetime:
    """Pick the end-point for the SLA window.

    - If the ticket has a terminal status (RESOLVED / CLOSED), the clock
      **stops** at that status timestamp, regardless of ``ref``.
    - Otherwise, if a ``ref`` is supplied (e.g. ``datetime.now(tz=timezone.utc)``),
      use that — the ticket is still "in flight."
    - Otherwise, use the last status-history timestamp, or the creation time
      if there is no history at all.
    """
    if ticket.status_history:
        last_entry = ticket.status_history[-1]
        if last_entry.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            return last_entry.at
        if ref is not None:
            return ref
        return last_entry.at
    # No history
    if ref is not None:
        return ref
    return ticket.created_at


# ── clock-interval construction ──────────────────────────────────────────────

def _active_intervals(
    ticket: Ticket, end: datetime
) -> list[tuple[datetime, datetime]]:
    """Build the list of ``(start, end)`` intervals during which the SLA clock
    was running, in chronological order.

    The clock starts at ``ticket.created_at`` and stops each time the ticket
    enters ON_HOLD.  It resumes when the ticket leaves ON_HOLD.  If the ticket
    is currently ON_HOLD the last interval has no resume point — it simply
    stops at the ON_HOLD entry time.
    """
    history = ticket.status_history

    # Default: one interval from creation to `end`
    if not history:
        return [(ticket.created_at, end)]

    # Walk the status timeline and split whenever ON_HOLD is entered/left
    intervals: list[tuple[datetime, datetime]] = []
    current_start: datetime | None = ticket.created_at

    for entry in history:
        at = entry.at

        if entry.status == TicketStatus.ON_HOLD and current_start is not None:
            # Clock pauses — close the current interval
            intervals.append((current_start, at))
            current_start = None

        elif entry.status != TicketStatus.ON_HOLD and current_start is None:
            # Clock resumes
            current_start = at

    # If the clock was still running at the last entry, close the final interval
    if current_start is not None:
        intervals.append((current_start, end))

    return intervals


# ── main calculator ──────────────────────────────────────────────────────────


def calculate_ticket_sla(
    ticket: Ticket,
    sla_policy: SlaPolicy,
    calendar: BusinessCalendar,
    ref: datetime | None = None,
) -> TicketReport:
    """Compute the SLA report for a single ticket.

    Parameters
    ----------
    ticket : Ticket
        A fully validated ``Ticket`` domain object.
    sla_policy : SlaPolicy
        Loaded and validated SLA policy.
    calendar : BusinessCalendar
        Configured business-days calendar.
    ref : datetime or None
        Reference point for "now".  If ``None``, the latest status timestamp is
        used (or the ticket creation time if no history exists).
    """
    end = _effective_end(ticket, ref)

    # Sum business minutes over all clock-running intervals
    elapsed = 0.0
    for seg_start, seg_end in _active_intervals(ticket, end):
        if seg_start < seg_end:
            elapsed += calendar.business_minutes_between(seg_start, seg_end)

    target = sla_policy.targets[ticket.priority]
    breached = elapsed > target
    breach_mins = max(0.0, elapsed - target) if breached else 0.0

    # Due-by = creation + SLA target in business minutes
    due_by = calendar.add_business_minutes(ticket.created_at, target)

    return TicketReport(
        ticket_id=ticket.ticket_id,
        priority=ticket.priority,
        assignee_group=ticket.assignee_group,
        elapsed_business_minutes=elapsed,
        sla_target_minutes=target,
        due_by=due_by,
        breached=breached,
        breach_minutes=breach_mins,
    )
