"""Analytics engine — breach % by priority and assignee group."""

from .models import TicketSLAResult, AnalyticsSummary


def compute_analytics(results: list[TicketSLAResult]) -> AnalyticsSummary:
    """Aggregate breach statistics across all ticket results."""

    by_priority: dict[str, dict] = {}
    by_assignee_group: dict[str, dict] = {}
    total = 0
    breached = 0
    all_elapsed: list[float] = []
    all_breach: list[float] = []

    for r in results:
        total += 1
        if r.is_breached:
            breached += 1
        all_elapsed.append(r.elapsed_business_minutes)
        if r.is_breached:
            all_breach.append(r.breach_minutes)

        # By priority
        pkey = r.priority
        if pkey not in by_priority:
            by_priority[pkey] = {"total": 0, "breached": 0, "elapsed_sum": 0.0}
        by_priority[pkey]["total"] += 1
        by_priority[pkey]["elapsed_sum"] += r.elapsed_business_minutes
        if r.is_breached:
            by_priority[pkey]["breached"] += 1

        # By assignee group
        akey = r.assignee_group
        if akey not in by_assignee_group:
            by_assignee_group[akey] = {"total": 0, "breached": 0, "elapsed_sum": 0.0}
        by_assignee_group[akey]["total"] += 1
        by_assignee_group[akey]["elapsed_sum"] += r.elapsed_business_minutes
        if r.is_breached:
            by_assignee_group[akey]["breached"] += 1

    # Compute rates and averages
    for d in [by_priority, by_assignee_group]:
        for k, v in d.items():
            v["breach_rate_pct"] = round(v["breached"] / v["total"] * 100, 2) if v["total"] else 0.0
            v["avg_elapsed_minutes"] = round(v["elapsed_sum"] / v["total"], 2) if v["total"] else 0.0
            del v["elapsed_sum"]

    overall = {
        "total_tickets": total,
        "breached": breached,
        "breach_rate_pct": round(breached / total * 100, 2) if total else 0.0,
        "avg_elapsed_minutes": round(sum(all_elapsed) / len(all_elapsed), 2) if all_elapsed else 0.0,
        "max_breach_minutes": round(max(all_breach), 2) if all_breach else 0.0,
        "avg_breach_minutes": round(sum(all_breach) / len(all_breach), 2) if all_breach else 0.0,
    }

    return AnalyticsSummary(
        by_priority=by_priority,
        by_assignee_group=by_assignee_group,
        overall=overall,
    )