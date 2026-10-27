"""Core SLA calculator — elapsed business minutes, due-by projection, breach detection."""

from datetime import datetime, timezone
from typing import Optional

from .calendar import (
    HolidayCalendar,
    business_minutes_between,
    project_due_by,
    clamp_to_business_hours,
)
from .models import Ticket, SLAPolicy, TicketSLAResult


def _normalize(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_ticket_sla(
    ticket: Ticket,
    policy: SLAPolicy,
    holidays: HolidayCalendar,
    as_of: Optional[datetime] = None,
) -> TicketSLAResult:
    """Compute SLA metrics for a single ticket.

    Algorithm:
    1. Normalize and sort transitions chronologically.
    2. Slice timeline into ACTIVE and ON_HOLD intervals.
    3. For each ACTIVE interval, accumulate business minutes via calendar engine.
    4. Project due-by by advancing from CREATED timestamp through active time.
    5. Determine breach status and breach minutes.
    """

    as_of = _normalize(as_of) if as_of else datetime.now(timezone.utc)
    target_minutes = policy.target_minutes(ticket.priority)

    if not ticket.transitions:
        # No transitions — treat as if just created, zero elapsed
        return TicketSLAResult(
            ticket_id=ticket.ticket_id,
            priority=ticket.priority,
            assignee_group=ticket.assignee_group,
            sla_target_minutes=target_minutes,
            elapsed_business_minutes=0.0,
            due_by=project_due_by(clamp_to_business_hours(as_of), target_minutes, holidays),
            is_breached=False,
            breach_minutes=0.0,
            as_of=as_of,
        )

    # Sort and deduplicate consecutive same-status transitions
    sorted_tr = sorted(ticket.transitions, key=lambda t: t.timestamp)
    deduped = [sorted_tr[0]]
    for t in sorted_tr[1:]:
        if t.status != deduped[-1].status:
            deduped.append(t)

    # Build active intervals: segments where status is NOT ON_HOLD
    active_intervals = []
    paused_minutes = 0.0
    resolved_at = None

    for i, tr in enumerate(deduped):
        if tr.status in ("RESOLVED", "CLOSED"):
            resolved_at = tr.timestamp
            break

    # Determine the effective end point
    eff_end = resolved_at if resolved_at else as_of
    eff_end = _normalize(eff_end)

    # Walk through transitions to build active intervals
    # Active segment starts at CREATED or after ON_HOLD→IN_PROGRESS
    in_active = False
    active_start = None
    on_hold_start = None

    for i, tr in enumerate(deduped):
        ts = _normalize(tr.timestamp)

        if tr.status in ("RESOLVED", "CLOSED"):
            # End the current segment
            if in_active and active_start is not None:
                active_intervals.append((active_start, ts))
                in_active = False
            if on_hold_start is not None:
                # ON_HOLD that was never resumed before resolution
                paused_minutes += (ts - on_hold_start).total_seconds() / 60
            break

        if tr.status == "ON_HOLD":
            if in_active and active_start is not None:
                active_intervals.append((active_start, ts))
                in_active = False
            on_hold_start = ts
        else:
            if on_hold_start is not None:
                paused_minutes += (ts - on_hold_start).total_seconds() / 60
                on_hold_start = None
            if not in_active:
                active_start = ts
                in_active = True

    # Handle tail: if still active at eff_end
    if in_active and active_start is not None:
        active_intervals.append((active_start, eff_end))
    if on_hold_start is not None:
        paused_minutes += (eff_end - on_hold_start).total_seconds() / 60

    # Compute elapsed business minutes across all active intervals
    elapsed = 0.0
    for astart, aend in active_intervals:
        elapsed += business_minutes_between(astart, aend, holidays)

    # Due-by: start from the first CREATED timestamp, projected forward
    created_ts = _normalize(deduped[0].timestamp)
    # Due-by projection through business minutes only (target)
    # But pauses shift the wall-clock due-by forward
    due_by = project_due_by(created_ts, target_minutes + elapsed, holidays)
    # Actually, due-by should be: start from created, advance through target_minutes
    # of business time, PLUS any pause gaps push the wall clock further.
    # The project_due_by already handles business-only advancement.
    # We need: due_by = project(created, target_minutes) then add pause wall-clock shift.
    # But simpler: project from created by (target_minutes + paused_business_time)
    # Actually the correct approach: project from created by target_minutes of business time,
    # then for each pause interval, the due-by slides forward by the wall-clock pause duration.
    due_by_base = project_due_by(created_ts, target_minutes, holidays)

    # Each pause interval pushes the due-by forward by its wall-clock duration
    pause_wall_shift = 0.0
    on_hold_start_2 = None
    for tr in deduped:
        ts = _normalize(tr.timestamp)
        if tr.status in ("RESOLVED", "CLOSED"):
            if on_hold_start_2 is not None:
                pause_wall_shift += (_normalize(tr.timestamp) - on_hold_start_2).total_seconds()
            break
        if tr.status == "ON_HOLD" and on_hold_start_2 is None:
            on_hold_start_2 = ts
        elif tr.status != "ON_HOLD" and on_hold_start_2 is not None:
            pause_wall_shift += (ts - on_hold_start_2).total_seconds()
            on_hold_start_2 = None
    if on_hold_start_2 is not None:
        pause_wall_shift += (eff_end - on_hold_start_2).total_seconds()

    from datetime import timedelta
    due_by = due_by_base + timedelta(seconds=pause_wall_shift)

    is_breached = elapsed > target_minutes
    breach_minutes = max(0.0, elapsed - target_minutes)

    return TicketSLAResult(
        ticket_id=ticket.ticket_id,
        priority=ticket.priority,
        assignee_group=ticket.assignee_group,
        sla_target_minutes=target_minutes,
        elapsed_business_minutes=round(elapsed, 2),
        due_by=due_by.replace(tzinfo=timezone.utc),
        is_breached=is_breached,
        breach_minutes=round(breach_minutes, 2),
        as_of=as_of,
        total_paused_minutes=round(paused_minutes, 2),
        resolved_at=_normalize(resolved_at) if resolved_at else None,
    )