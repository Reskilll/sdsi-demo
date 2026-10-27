"""Aggregation (M5) and output rendering (JSON / CSV / table)."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Iterable, Sequence

from .models import SlaPolicy, TicketError, TicketResult
from .timeutil import to_iso

_CSV_COLUMNS = (
    "ticket_id", "priority", "assignee_group", "current_status", "clock_state",
    "target_minutes", "elapsed_business_minutes", "on_hold_business_minutes",
    "remaining_minutes", "due_by", "breached", "breach_minutes", "at_risk",
)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _empty_bucket() -> dict:
    return {"total": 0, "breached": 0, "open": 0, "at_risk": 0, "_elapsed": 0}


def _add(bucket: dict, r: TicketResult) -> None:
    bucket["total"] += 1
    bucket["breached"] += r.breached
    bucket["open"] += r.is_open
    bucket["at_risk"] += r.at_risk
    bucket["_elapsed"] += r.elapsed_seconds


def _finalize(bucket: dict) -> dict:
    total = bucket["total"]
    return {
        "total": total,
        "breached": bucket["breached"],
        "breach_pct": round(100 * bucket["breached"] / total, 2) if total else None,
        "open": bucket["open"],
        "at_risk": bucket["at_risk"],
        "avg_elapsed_business_minutes": round(bucket["_elapsed"] / total / 60, 2) if total else None,
    }


def summarize(results: Iterable[TicketResult], priorities: Sequence[str]) -> dict:
    """Breach % overall, per priority and per assignee group.

    Every configured priority is listed (``breach_pct`` is ``None`` when it has
    no tickets) so consumers never see a priority silently disappear.
    """
    overall = _empty_bucket()
    by_priority = {p: _empty_bucket() for p in priorities}
    by_group: dict[str, dict] = {}
    for r in results:
        _add(overall, r)
        _add(by_priority.setdefault(r.priority, _empty_bucket()), r)
        _add(by_group.setdefault(r.assignee_group, _empty_bucket()), r)
    return {
        "overall": _finalize(overall),
        "by_priority": {k: _finalize(v) for k, v in by_priority.items()},
        "by_assignee_group": {k: _finalize(by_group[k]) for k in sorted(by_group)},
    }


def build_report(
    results: list[TicketResult], errors: list[TicketError], policy: SlaPolicy, as_of: datetime
) -> dict:
    return {
        "as_of": to_iso(as_of, policy.timezone),
        "timezone": policy.timezone_name,
        "tickets": [r.to_dict(policy.timezone) for r in results],
        "summary": summarize(results, list(policy.targets_minutes)),
        "errors": [e.to_dict() for e in errors],
    }


# --------------------------------------------------------------------------- renderers
def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def _csv_safe(value: object) -> object:
    """Neutralise spreadsheet formula injection (CWE-1236)."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def render_csv(report: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    for row in report["tickets"]:
        writer.writerow(_csv_safe(row[c]) for c in _CSV_COLUMNS)
    return buf.getvalue()


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "YES" if value else "no"
    return str(value)


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    cells = [[_fmt(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    line = lambda vals: "  ".join(v.ljust(w) for v, w in zip(vals, widths)).rstrip()
    out = [line(headers), line(["-" * w for w in widths])]
    out.extend(line(r) for r in cells)
    return "\n".join(out)


def _summary_rows(section: dict) -> list[list[object]]:
    return [
        [k, v["total"], v["breached"], v["breach_pct"], v["open"], v["at_risk"]]
        for k, v in section.items()
    ]


def render_table(report: dict) -> str:
    ticket_rows = [
        [t["ticket_id"], t["priority"], t["assignee_group"], t["current_status"],
         t["clock_state"], t["elapsed_business_minutes"], t["target_minutes"],
         t["due_by"], t["breached"], t["breach_minutes"], t["at_risk"]]
        for t in report["tickets"]
    ]
    summary = report["summary"]
    overall = summary["overall"]
    sum_headers = ["KEY", "TOTAL", "BREACHED", "BREACH_%", "OPEN", "AT_RISK"]
    parts = [
        f"SLA report as of {report['as_of']} (timezone {report['timezone']})",
        "",
        _table(["TICKET", "PRI", "GROUP", "STATUS", "CLOCK", "ELAPSED_MIN",
                "TARGET_MIN", "DUE_BY", "BREACHED", "BREACH_MIN", "AT_RISK"], ticket_rows),
        "",
        "Summary by priority",
        _table(sum_headers, _summary_rows(summary["by_priority"])),
        "",
        "Summary by assignee group",
        _table(sum_headers, _summary_rows(summary["by_assignee_group"])),
        "",
        f"Overall: {overall['breached']}/{overall['total']} breached "
        f"({_fmt(overall['breach_pct'])}%), {overall['at_risk']} at risk",
    ]
    if report["errors"]:
        parts += ["", f"Rejected tickets ({len(report['errors'])})"]
        parts += [f"  - {e['ticket']}: {e['error']}" for e in report["errors"]]
    return "\n".join(parts) + "\n"


RENDERERS = {"json": render_json, "csv": render_csv, "table": render_table}

