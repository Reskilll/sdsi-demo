"""Multi-format reporter: terminal (ANSI), JSON, CSV, HTML dashboard."""

import json
import csv
import io
from datetime import datetime
from typing import Optional

from .models import TicketSLAResult, AnalyticsSummary


# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def print_cli_report(
    results: list[TicketSLAResult],
    analytics: AnalyticsSummary,
    filters: Optional[dict] = None,
) -> None:
    """Print colored terminal report."""

    # Filter if requested
    filtered = results
    if filters:
        if "priority" in filters:
            filtered = [r for r in filtered if r.priority == filters["priority"]]
        if "assignee_group" in filters:
            filtered = [r for r in filtered if r.assignee_group == filters["assignee_group"]]
        if "breached" in filters:
            filtered = [r for r in filtered if r.is_breached == filters["breached"]]

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║          IT SERVICE-DESK SLA TRACKER — REPORT              ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}\n")

    # Overall summary cards
    o = analytics.overall
    print(f"{BOLD}OVERALL HEALTH{RESET}")
    print(f"  Total Tickets:    {o['total_tickets']}")
    color = RED if o['breach_rate_pct'] > 20 else (YELLOW if o['breach_rate_pct'] > 5 else GREEN)
    print(f"  Breach Rate:      {color}{o['breach_rate_pct']}%{RESET}")
    print(f"  Avg Elapsed:      {o['avg_elapsed_minutes']} min")
    print(f"  Max Breach:       {o['max_breach_minutes']} min")
    print(f"  Avg Breach:       {o['avg_breach_minutes']} min")
    print()

    # By Priority
    print(f"{BOLD}BY PRIORITY{RESET}")
    print(f"  {'Priority':<10} {'Total':<8} {'Breached':<10} {'Rate':<10} {'Avg Elapsed'}")
    print(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*10} {'-'*15}")
    for priority, stats in sorted(analytics.by_priority.items()):
        color = RED if stats['breach_rate_pct'] > 20 else (YELLOW if stats['breach_rate_pct'] > 5 else GREEN)
        print(f"  {priority:<10} {stats['total']:<8} {stats['breached']:<10} "
              f"{color}{stats['breach_rate_pct']}%{RESET:<6} {stats['avg_elapsed_minutes']} min")
    print()

    # By Assignee Group
    print(f"{BOLD}BY ASSIGNEE GROUP{RESET}")
    print(f"  {'Group':<25} {'Total':<8} {'Breached':<10} {'Rate':<10} {'Avg Elapsed'}")
    print(f"  {'-'*25} {'-'*8} {'-'*10} {'-'*10} {'-'*15}")
    for group, stats in sorted(analytics.by_assignee_group.items()):
        color = RED if stats['breach_rate_pct'] > 20 else (YELLOW if stats['breach_rate_pct'] > 5 else GREEN)
        name = group if len(group) <= 25 else group[:22] + "..."
        print(f"  {name:<25} {stats['total']:<8} {stats['breached']:<10} "
              f"{color}{stats['breach_rate_pct']}%{RESET:<6} {stats['avg_elapsed_minutes']} min")
    print()

    # Per-ticket table
    print(f"{BOLD}PER-TICKET DETAIL{RESET} ({len(filtered)} tickets)")
    print(f"  {'ID':<20} {'P':<4} {'Group':<18} {'Elapsed':<10} {'Target':<10} "
          f"{'Status':<12} {'Breach':<10} {'Due By'}")
    print(f"  {'-'*20} {'-'*4} {'-'*18} {'-'*10} {'-'*10} {'-'*12} {'-'*10} {'-'*20}")
    for r in filtered:
        status_str = f"{RED}BREACHED{RESET}" if r.is_breached else f"{GREEN}OK{RESET}"
        breach_str = f"{RED}{r.breach_minutes} min{RESET}" if r.is_breached else "-"
        print(f"  {r.ticket_id:<20} {r.priority:<4} {r.assignee_group:<18} "
              f"{r.elapsed_business_minutes:<10.0f} {r.sla_target_minutes:<10} "
              f"{status_str:<24} {breach_str:<18} {_fmt_dt(r.due_by)}")
    print()


def to_json_report(
    results: list[TicketSLAResult],
    analytics: AnalyticsSummary,
) -> str:
    """Generate JSON report string."""
    return json.dumps({
        "generated_at": datetime.now().isoformat(),
        "analytics": analytics.to_dict(),
        "tickets": [r.to_dict() for r in results],
    }, indent=2)


def to_csv_report(results: list[TicketSLAResult]) -> str:
    """Generate CSV report string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ticket_id", "priority", "assignee_group", "sla_target_minutes",
        "elapsed_business_minutes", "due_by", "is_breached", "breach_minutes",
        "as_of", "total_paused_minutes", "resolved_at",
    ])
    for r in results:
        writer.writerow([
            r.ticket_id, r.priority, r.assignee_group, r.sla_target_minutes,
            r.elapsed_business_minutes, r.due_by.isoformat(), r.is_breached,
            r.breach_minutes, r.as_of.isoformat(), r.total_paused_minutes,
            r.resolved_at.isoformat() if r.resolved_at else "",
        ])
    return output.getvalue()


def to_html_report(
    results: list[TicketSLAResult],
    analytics: AnalyticsSummary,
) -> str:
    """Generate standalone HTML dashboard with dark mode support."""

    tickets_json = json.dumps([r.to_dict() for r in results])
    analytics_json = json.dumps(analytics.to_dict())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SLA Tracker — Executive Dashboard</title>
<style>
:root {{
  --bg: #ffffff; --fg: #1a1a2e; --card: #f8f9fa; --border: #dee2e6;
  --red: #dc3545; --green: #28a745; --yellow: #ffc107; --accent: #0d6efd;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #1a1a2e; --fg: #e0e0e0; --card: #16213e; --border: #2a2a4a; }}
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg); color: var(--fg); padding: 24px; }}
h1 {{ margin-bottom: 8px; font-size: 1.5rem; }}
h2 {{ margin: 24px 0 12px; font-size: 1.1rem; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
.card .value {{ font-size: 2rem; font-weight: bold; }}
.card .label {{ font-size: 0.85rem; color: #888; margin-top: 4px; }}
.breach {{ color: var(--red); }}
.ok {{ color: var(--green); }}
.warn {{ color: var(--yellow); }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.9rem; }}
th, td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; }}
th {{ font-weight: 600; background: var(--card); }}
.status-breached {{ color: var(--red); font-weight: bold; }}
.status-ok {{ color: var(--green); }}
</style>
</head>
<body>
<h1>🎯 IT Service-Desk SLA Tracker — Dashboard</h1>
<p style="color:#888;margin-bottom:16px;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<div id="cards"></div>

<h2>📊 Breach Rate by Priority</h2>
<table id="by-priority">
<tr><th>Priority</th><th>Total</th><th>Breached</th><th>Rate</th><th>Avg Elapsed</th></tr>
</table>

<h2>👥 Breach Rate by Assignee Group</h2>
<table id="by-group">
<tr><th>Group</th><th>Total</th><th>Breached</th><th>Rate</th><th>Avg Elapsed</th></tr>
</table>

<h2>🎫 Per-Ticket Details</h2>
<table id="tickets">
<tr><th>Ticket ID</th><th>Priority</th><th>Group</th><th>Elapsed</th><th>Target</th><th>Status</th><th>Breach</th><th>Due By</th></tr>
</table>

<script>
const tickets = {tickets_json};
const analytics = {analytics_json};

// Overall cards
const o = analytics.overall;
const rateClass = o.breach_rate_pct > 20 ? 'breach' : (o.breach_rate_pct > 5 ? 'warn' : 'ok');
document.getElementById('cards').innerHTML = `
<div class="card"><div class="value">${{o.total_tickets}}</div><div class="label">Total Tickets</div></div>
<div class="card"><div class="value ${{rateClass}}">${{o.breach_rate_pct}}%</div><div class="label">Breach Rate</div></div>
<div class="card"><div class="value">${{o.avg_elapsed_minutes}}</div><div class="label">Avg Elapsed (min)</div></div>
<div class="card"><div class="value breach">${{o.max_breach_minutes}}</div><div class="label">Max Breach (min)</div></div>
`;

// Priority table
let phtml = '';
for (const [k, v] of Object.entries(analytics.by_priority).sort()) {{
  const rc = v.breach_rate_pct > 20 ? 'breach' : (v.breach_rate_pct > 5 ? 'warn' : 'ok');
  phtml += `<tr><td>${{k}}</td><td>${{v.total}}</td><td>${{v.breached}}</td><td class="${{rc}}">${{v.breach_rate_pct}}%</td><td>${{v.avg_elapsed_minutes}} min</td></tr>`;
}}
document.getElementById('by-priority').innerHTML += phtml;

// Group table
let ghtml = '';
for (const [k, v] of Object.entries(analytics.by_assignee_group).sort()) {{
  const rc = v.breach_rate_pct > 20 ? 'breach' : (v.breach_rate_pct > 5 ? 'warn' : 'ok');
  ghtml += `<tr><td>${{k}}</td><td>${{v.total}}</td><td>${{v.breached}}</td><td class="${{rc}}">${{v.breach_rate_pct}}%</td><td>${{v.avg_elapsed_minutes}} min</td></tr>`;
}}
document.getElementById('by-group').innerHTML += ghtml;

// Tickets table
let thtml = '';
for (const t of tickets) {{
  const sc = t.is_breached ? 'status-breached' : 'status-ok';
  const bc = t.is_breached ? `<span class="breach">${{t.breach_minutes}} min</span>` : '-';
  thtml += `<tr><td>${{t.ticket_id}}</td><td>${{t.priority}}</td><td>${{t.assignee_group}}</td>
    <td>${{t.elapsed_business_minutes}}</td><td>${{t.sla_target_minutes}}</td>
    <td class="${{sc}}">${{t.is_breached ? 'BREACHED' : 'OK'}}</td><td>${{bc}}</td>
    <td>${{t.due_by}}</td></tr>`;
}}
document.getElementById('tickets').innerHTML += thtml;
</script>
</body>
</html>"""