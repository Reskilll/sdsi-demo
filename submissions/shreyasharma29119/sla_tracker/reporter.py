"""Summary reporting (M5).

Produces:
  - Per-ticket table (M4)
  - Breach % per priority
  - Breach % per assignee group
"""

from __future__ import annotations

from collections import defaultdict

from .models import TicketSlaResult


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


# ---- M4: per-ticket report --------------------------------------------------


def format_ticket_report(results: list[TicketSlaResult]) -> str:
    """Return a formatted table of per-ticket SLA results."""
    if not results:
        return "No results to display."

    header = (
        f"{'Ticket':<10} {'Priority':<10} {'Group':<16} "
        f"{'Elapsed(min)':>13} {'Target(min)':>12} {'Due By':<20} "
        f"{'Breach':>8} {'Breach(min)':>12}"
    )
    sep = "-" * len(header)
    lines = [header, sep]

    for r in results:
        lines.append(
            f"{r.ticket_id:<10} {r.priority:<10} {r.assignee_group:<16} "
            f"{r.elapsed_business_minutes:>13} {r.target_minutes:>12} "
            f"{r.due_by.strftime('%Y-%m-%d %H:%M'):<20} "
            f"{'YES' if r.breached else 'no':>8} "
            f"{r.breach_minutes:>12}"
        )

    return "\n".join(lines)


# ---- M5: summary ------------------------------------------------------------


def build_summary(results: list[TicketSlaResult]) -> dict:
    """Return a dict with breach percentages by priority and by group."""
    by_priority: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "breached": 0}
    )
    by_group: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "breached": 0}
    )

    for r in results:
        by_priority[r.priority]["total"] += 1
        by_group[r.assignee_group]["total"] += 1
        if r.breached:
            by_priority[r.priority]["breached"] += 1
            by_group[r.assignee_group]["breached"] += 1

    return {
        "by_priority": {
            p: {
                "total": v["total"],
                "breached": v["breached"],
                "breach_pct": _pct(v["breached"], v["total"]),
            }
            for p, v in sorted(by_priority.items())
        },
        "by_group": {
            g: {
                "total": v["total"],
                "breached": v["breached"],
                "breach_pct": _pct(v["breached"], v["total"]),
            }
            for g, v in sorted(by_group.items())
        },
    }


def format_summary(results: list[TicketSlaResult]) -> str:
    """Return a human-readable summary string."""
    s = build_summary(results)
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("SLA SUMMARY")
    lines.append("=" * 60)

    # By priority
    lines.append(f"\n{'Breach % by Priority':<30}")
    lines.append("-" * 40)
    lines.append(f"  {'Priority':<10} {'Total':>6} {'Breached':>10} {'%':>8}")
    for p, d in s["by_priority"].items():
        lines.append(
            f"  {p:<10} {d['total']:>6} {d['breached']:>10} {d['breach_pct']:>7.1f}%"
        )

    # By group
    lines.append(f"\n{'Breach % by Assignee Group':<30}")
    lines.append("-" * 40)
    lines.append(f"  {'Group':<16} {'Total':>6} {'Breached':>10} {'%':>8}")
    for g, d in s["by_group"].items():
        lines.append(
            f"  {g:<16} {d['total']:>6} {d['breached']:>10} {d['breach_pct']:>7.1f}%"
        )

    lines.append("=" * 60)
    return "\n".join(lines)