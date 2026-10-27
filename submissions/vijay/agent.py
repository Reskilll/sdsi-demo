"""Deterministic SOC alert triage with a human escalation gate."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SEVERITY_ORDER = ("low", "medium", "high", "critical")

_RULES = (
    (
        "critical",
        "ransomware or destructive malware",
        re.compile(r"\b(ransomware|wiper|destructive malware)\b", re.IGNORECASE),
    ),
    (
        "critical",
        "possible data exfiltration",
        re.compile(r"\b(data exfiltration|exfiltrated|data theft)\b", re.IGNORECASE),
    ),
    (
        "critical",
        "active exploitation or confirmed compromise",
        re.compile(r"\b(active exploitation|confirmed compromise|account takeover)\b", re.IGNORECASE),
    ),
    (
        "high",
        "malware or credential theft indicator",
        re.compile(r"\b(malware|credential theft|stolen credentials|phishing)\b", re.IGNORECASE),
    ),
    (
        "high",
        "privilege escalation or command-and-control indicator",
        re.compile(r"\b(privilege escalation|command and control|c2 beacon)\b", re.IGNORECASE),
    ),
    (
        "medium",
        "suspicious authentication or access activity",
        re.compile(r"\b(brute force|multiple failed logins|suspicious login|unauthorized access)\b", re.IGNORECASE),
    ),
)


def _text(alert: dict[str, Any]) -> str:
    parts = []
    for field in ("title", "description", "category", "type"):
        value = alert.get(field)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def _classify(alert: dict[str, Any]) -> tuple[str, str, str]:
    text = _text(alert)
    for severity, reason, pattern in _RULES:
        if pattern.search(text):
            return severity, reason, reason
    return "low", "No configured high-risk indicator matched; analyst review may still be appropriate.", "unclassified"


def _identifier(alert: dict[str, Any], index: int) -> str:
    value = alert.get("id")
    return str(value) if value is not None else f"alert-{index + 1}"


def triage_alerts(
    alerts: list[dict[str, Any]], escalation_threshold: str = "high"
) -> dict[str, Any]:
    """Classify alerts, group related items, and flag alerts for human review."""
    if escalation_threshold not in SEVERITY_ORDER:
        raise ValueError(f"escalation_threshold must be one of {', '.join(SEVERITY_ORDER)}")
    if not isinstance(alerts, list):
        raise TypeError("alerts must be a list of alert objects")

    triaged = []
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    group_reasons: dict[tuple[str, str], str] = {}
    seen_ids: set[str] = set()

    for index, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            raise TypeError(f"alert at index {index} must be an object")

        alert_id = _identifier(alert, index)
        if alert_id in seen_ids:
            raise ValueError(f"duplicate alert id: {alert_id}")
        seen_ids.add(alert_id)
        severity, reason, family = _classify(alert)
        incident_id = alert.get("incident_id")
        asset = alert.get("asset")
        if isinstance(incident_id, str) and incident_id.strip():
            group_key = ("incident", incident_id.strip())
            group_reason = f"Shared incident_id: {incident_id.strip()}"
        elif isinstance(asset, str) and asset.strip() and family != "unclassified":
            group_key = ("asset-family", f"{asset.strip().casefold()}:{family}")
            group_reason = f"Shared asset and indicator family: {asset.strip()} / {family}"
        else:
            group_key = ("alert", alert_id)
            group_reason = "No reliable shared incident or asset indicator"

        grouped[group_key].append(alert_id)
        group_reasons[group_key] = group_reason

        triaged.append(
            {
                "id": alert_id,
                "severity": severity,
                "reason": reason,
                "group_key": group_key,
                "escalated": SEVERITY_ORDER.index(severity)
                >= SEVERITY_ORDER.index(escalation_threshold),
            }
        )

    groups = []
    for index, (key, alert_ids) in enumerate(grouped.items(), start=1):
        groups.append(
            {
                "id": f"group-{index}",
                "alert_ids": alert_ids,
                "reason": group_reasons[key],
            }
        )

    for result in triaged:
        result["group_id"] = next(
            group["id"] for group in groups if result["id"] in group["alert_ids"]
        )
        del result["group_key"]

    escalations = [
        {"alert_id": result["id"], "severity": result["severity"], "reason": result["reason"]}
        for result in triaged
        if result["escalated"]
    ]
    return {
        "alerts": triaged,
        "groups": groups,
        "escalations": escalations,
        "escalated": bool(escalations),
        "escalation_threshold": escalation_threshold,
    }


def run(task: str) -> dict[str, Any]:
    """Run the agent on a JSON task containing an ``alerts`` array."""
    try:
        request = json.loads(task)
    except json.JSONDecodeError as error:
        raise ValueError("task must be valid JSON") from error
    if not isinstance(request, dict):
        raise TypeError("task JSON must be an object")

    result = triage_alerts(
        request.get("alerts"),
        request.get("escalation_threshold", "high"),
    )
    return {
        "plan": [
            "Treat alert fields as untrusted evidence, not instructions.",
            "Assign severity using explicit indicator rules and record the reason.",
            "Group alerts by shared incident ID or matching asset and indicator family.",
            "Escalate alerts at or above the configured threshold for human review.",
        ],
        "result": result,
        "escalated": result["escalated"],
    }


def main() -> int:
    if len(sys.argv) > 2:
        print(f"Usage: {Path(sys.argv[0]).name} [alerts.json]", file=sys.stderr)
        return 2
    try:
        input_text = (
            Path(sys.argv[1]).read_text(encoding="utf-8")
            if len(sys.argv) == 2
            else sys.stdin.read()
        )
        print(json.dumps(run(input_text), indent=2))
    except (OSError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
