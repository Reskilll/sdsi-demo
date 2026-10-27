"""Report generation — per-ticket details and aggregate summaries."""

from __future__ import annotations

from collections.abc import Iterable

from sla_tracker.models import (
    GroupBreachSummary,
    Priority,
    PriorityBreachSummary,
    SummaryReport,
    TicketReport,
)


def build_summary(reports: Iterable[TicketReport]) -> SummaryReport:
    """Aggregate per-ticket reports into priority and group summaries."""
    reports = list(reports)
    total = len(reports)

    if total == 0:
        return SummaryReport(
            by_priority=[PriorityBreachSummary(p, 0, 0, 0.0) for p in Priority],
            by_group=[],
            total_tickets=0,
            overall_breach_pct=0.0,
        )

    # By priority
    by_priority: list[PriorityBreachSummary] = []
    for p in Priority:
        subset = [r for r in reports if r.priority == p]
        ct = len(subset)
        breached_ct = sum(1 for r in subset if r.breached)
        by_priority.append(
            PriorityBreachSummary(
                priority=p,
                total=ct,
                breached=breached_ct,
                breach_pct=(breached_ct / ct * 100) if ct else 0.0,
            )
        )

    # By group
    groups: dict[str, list[TicketReport]] = {}
    for r in reports:
        groups.setdefault(r.assignee_group, []).append(r)
    by_group: list[GroupBreachSummary] = []
    for g, subset in sorted(groups.items()):
        ct = len(subset)
        breached_ct = sum(1 for r in subset if r.breached)
        by_group.append(
            GroupBreachSummary(
                group=g,
                total=ct,
                breached=breached_ct,
                breach_pct=breached_ct / ct * 100,
            )
        )

    overall_breached = sum(1 for r in reports if r.breached)
    overall_pct = overall_breached / total * 100

    return SummaryReport(
        by_priority=by_priority,
        by_group=by_group,
        total_tickets=total,
        overall_breach_pct=overall_pct,
    )


def format_ticket_report(report: TicketReport) -> str:
    """Format a single ticket report for display."""
    lines = [
        f"Ticket: {report.ticket_id}",
        f"  Priority:           P{report.priority.value}",
        f"  Assignee Group:     {report.assignee_group}",
        f"  Elapsed (bus. min): {report.elapsed_business_minutes:.1f}",
        f"  SLA Target (min):   {report.sla_target_minutes}",
        f"  Due By (UTC):       {report.due_by.isoformat()}",
        f"  Breached:           {'YES' if report.breached else 'NO'}",
    ]
    if report.breached:
        lines.append(f"  Breach Minutes:     {report.breach_minutes:.1f}")
    return "\n".join(lines)


def format_summary(summary: SummaryReport) -> str:
    """Format the aggregate summary for display."""
    lines = ["=== SLA Summary ===", f"Total Tickets: {summary.total_tickets}"]
    if summary.total_tickets > 0:
        lines.append(f"Overall Breach %: {summary.overall_breach_pct:.1f}%")

    lines.append("")
    lines.append("--- By Priority ---")
    for ps in summary.by_priority:
        lines.append(
            f"  P{ps.priority.value}: {ps.breached}/{ps.total} breached "
            f"({ps.breach_pct:.1f}%)"
        )

    lines.append("")
    lines.append("--- By Assignee Group ---")
    if summary.by_group:
        for gs in summary.by_group:
            lines.append(
                f"  {gs.group}: {gs.breached}/{gs.total} breached "
                f"({gs.breach_pct:.1f}%)"
            )
    else:
        lines.append("  (no groups)")

    return "\n".join(lines)
