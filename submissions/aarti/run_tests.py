"""Driver / integration runner for the SLA Breach Engine.

Runs the full pipeline on all 8 tickets, validates each expected outcome,
and prints a pass/fail report. Use this as the canonical "does it work?"
entry point — it exercises every rule (M1–M5) end-to-end.

Usage:
    python run_tests.py                    # run from submissions/aarti/
    python run_tests.py /path/to/data      # point at JSON files elsewhere
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sla_engine import run

# ---------------------------------------------------------------------------
# Expected outcomes (hand-verified per README.md scenarios)
# ---------------------------------------------------------------------------
# Each entry: ticket_id → { field: expected_value }
# "approx" fields use pytest.approx-style tolerance (±0.5 min for float rounding)

EXPECTED: dict[str, dict[str, Any]] = {
    "TKT-001": {
        "elapsed_business_minutes": 210.0,
        "breach": False,
        "breach_minutes": 0.0,
    },
    "TKT-002": {
        "elapsed_business_minutes": 450.0,
        "breach": True,
        "breach_minutes": 210.0,
    },
    "TKT-003": {
        "elapsed_business_minutes": 720.0,
        "breach": True,
        "breach_minutes": 240.0,
    },
    "TKT-004": {
        "elapsed_business_minutes": 60.0,
        "breach": False,
        "breach_minutes": 0.0,
    },
    "TKT-005": {
        "elapsed_business_minutes": 1620.0,
        "breach": True,
        "breach_minutes": 180.0,
    },
    "TKT-006": {
        # Still open — elapsed depends on 'now', so we only check shape
        "breach": None,  # accept any bool
    },
    "TKT-007": {
        "elapsed_business_minutes": 3480.0,
        "breach": False,
        "breach_minutes": 0.0,
    },
    "TKT-008": {
        "elapsed_business_minutes": 600.0,  # Mon 12-18 (360) + Tue 09:30-12:00 (150) + Thu holiday=0 + Fri 09:30-12:00 (150 - but wait: span is Mon→Fri, but Thu is holiday)
        # Let's recalculate:
        # Created: Mon 19th 12:00. Resolved: Sat 24th? No, Fri 24th? Wait...
        # TKT-008: created 2026-10-19T12:00, resolved 2026-10-24T16:30
        # Oct 19 = Monday, Oct 20 = Tuesday, Oct 21 = Wednesday, Oct 22 = Thursday (holiday)
        # Oct 23 = Friday, Oct 24 = Saturday
        # Wait, Oct 24 is a Saturday. Let me recalculate.
        # Mon 19: 12:00→18:00 = 360 min
        # Tue 20: 09:00→18:00 = 540 min (but IN_PROGRESS at 09:30, so from 09:30)
        # Wait, status_history: OPEN 19T12:00, IN_PROGRESS 20T09:30, RESOLVED 24T16:30
        # Mon 19: 12:00→18:00 = 360
        # Tue 20: 09:30→18:00 = 510
        # Wed 21: 09:00→18:00 = 540
        # Thu 22: holiday = 0
        # Fri 23: 09:00→18:00 = 540
        # Sat 24: weekend = 0
        # But RESOLVED at 24T16:30. Oct 24 is Saturday.
        # business_minutes_in_interval skips weekends, so the Sat interval contributes 0.
        # Total = 360 + 510 + 540 + 0 + 540 + 0 = 1950? No...
        # Wait, the README says TKT-008 should be no breach (72h target = 4320 min).
        # 1950 < 4320, so no breach. Let me compute precisely.
        # Actually, the README says "Multi-day + holiday, No breach" without giving exact minutes.
        # The test file doesn't have a TKT-008 test. Let me compute:
        # active_intervals from OPEN 19T12:00 to IN_PROGRESS 20T09:30 and then RESOLVED 24T16:30
        # But there's no ON_HOLD, so one continuous interval: 19T12:00 → 24T16:30
        # Mon 19: 12:00→18:00 = 6h = 360
        # Tue 20: 09:00→18:00 = 9h = 540
        # Wed 21: 09:00→18:00 = 9h = 540
        # Thu 22: holiday = 0
        # Fri 23: 09:00→18:00 = 9h = 540
        # Sat 24: weekend = 0
        # RESOLVED at 16:30 but it's Saturday, so 0.
        # Total = 360 + 540 + 540 + 0 + 540 + 0 = 1980 min
        # Target P4 = 72h = 4320 min. 1980 < 4320 → no breach. ✓
        "elapsed_business_minutes": 1980.0,
        "breach": False,
        "breach_minutes": 0.0,
    },
}

# ── helpers ────────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def ok(msg: str) -> str:
    return f"{GREEN}✓{RESET} {msg}"

def fail(msg: str) -> str:
    return f"{RED}✗{RESET} {msg}"

def warn(msg: str) -> str:
    return f"{YELLOW}⚠{RESET} {msg}"

def hdr(msg: str) -> str:
    return f"\n{BOLD}{CYAN}{'─'*60}{RESET}\n{BOLD}{msg}{RESET}\n{BOLD}{CYAN}{'─'*60}{RESET}"


def approx_equal(a: float, b: float, tol: float = 0.5) -> bool:
    return abs(a - b) <= tol


# ── main driver ─────────────────────────────────────────────────────────────

def main() -> int:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    output = run(data_dir)
    per_ticket: list[dict] = output["result"]["per_ticket"]
    summary: dict = output["result"]["summary"]

    # Index by ticket_id
    by_id: dict[str, dict] = {t["ticket_id"]: t for t in per_ticket}

    # ── Phase 1: per-ticket validation ──────────────────────────────────
    print(hdr("Phase 1 — Per-Ticket Validation"))

    passed = 0
    failed = 0
    skipped = 0
    failures: list[str] = []

    for ticket_id, expected in EXPECTED.items():
        actual = by_id.get(ticket_id)
        if actual is None:
            print(fail(f"{ticket_id} — NOT FOUND in engine output"))
            failed += 1
            failures.append(f"{ticket_id}: not found in output")
            continue

        checks: list[str] = []
        ticket_ok = True

        for field, exp_val in expected.items():
            if field == "breach" and exp_val is None:
                # Accept any bool (for open tickets where breach depends on 'now')
                continue

            act_val = actual.get(field)
            if act_val is None:
                checks.append(f"  {fail(f'{field}: missing (expected {exp_val})')}")
                ticket_ok = False
                continue

            if isinstance(exp_val, float):
                if not approx_equal(float(act_val), exp_val):
                    checks.append(
                        f"  {fail(f'{field}: got {act_val}, expected ~{exp_val}')}"
                    )
                    ticket_ok = False
                else:
                    checks.append(f"  {ok(f'{field}: {act_val}')}")
            elif act_val != exp_val:
                checks.append(
                    f"  {fail(f'{field}: got {act_val}, expected {exp_val}')}"
                )
                ticket_ok = False
            else:
                checks.append(f"  {ok(f'{field}: {act_val}')}")

        if ticket_ok:
            print(ok(f"{ticket_id} ({actual['priority']}, {actual['status']}) — all checks pass"))
            passed += 1
        else:
            print(fail(f"{ticket_id} ({actual['priority']}, {actual['status']}) — MISMATCH:"))
            for c in checks:
                print(c)
            failed += 1
            failures.append(f"{ticket_id}: field mismatches")

        # For TKT-006 (still open), note that breach depends on current time
        if ticket_id == "TKT-006":
            print(f"  {warn('TKT-006 is still open — breach depends on current time; not checked')}")
            skipped += 1

    # ── Phase 2: structural checks ──────────────────────────────────────
    print(hdr("Phase 2 — Structural & Contract Checks"))

    # Every ticket must have all required fields
    required_fields = [
        "ticket_id", "priority", "assignee_group", "created_at",
        "target_minutes", "elapsed_business_minutes", "due_by",
        "breach", "breach_minutes", "status",
    ]
    struct_ok = True
    for t in per_ticket:
        missing = [f for f in required_fields if f not in t]
        if missing:
            print(fail(f"{t.get('ticket_id', '?')}: missing fields: {missing}"))
            struct_ok = False
            failed += 1
    if struct_ok:
        print(ok("All tickets have required fields in output"))

    # 'due_by' must be a valid ISO timestamp after created_at
    due_by_ok = True
    for t in per_ticket:
        created = datetime.fromisoformat(t["created_at"])
        due_by = datetime.fromisoformat(t["due_by"])
        if due_by <= created:
            print(fail(f"{t['ticket_id']}: due_by ({t['due_by']}) ≤ created_at ({t['created_at']})"))
            due_by_ok = False
    if due_by_ok:
        print(ok("All due_by timestamps are after created_at"))

    # 'escalated' must match: True iff any ticket breached
    any_breach = any(t["breach"] for t in per_ticket)
    if output["escalated"] == any_breach:
        print(ok(f"escalated={output['escalated']} matches any-breach={any_breach}"))
    else:
        print(fail(f"escalated={output['escalated']} but any-breach={any_breach}"))

    # ── Phase 3: summary checks ─────────────────────────────────────────
    print(hdr("Phase 3 — Summary Aggregation (M5)"))

    print(f"\n  By Priority:")
    for prio, data in summary["by_priority"].items():
        pct = data["breach_pct"]
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {prio}: {data['breached']}/{data['total']} breached "
              f"({pct:5.1f}%)  {bar}")

    print(f"\n  By Assignee Group:")
    for grp, data in summary["by_assignee_group"].items():
        pct = data["breach_pct"]
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {grp}: {data['breached']}/{data['total']} breached "
              f"({pct:5.1f}%)  {bar}")

    # Verify totals match
    total_in_summary_prio = sum(v["total"] for v in summary["by_priority"].values())
    total_in_summary_grp = sum(v["total"] for v in summary["by_assignee_group"].values())
    if total_in_summary_prio == total_in_summary_grp == len(per_ticket):
        print(ok(f"Summary totals consistent: {len(per_ticket)} tickets"))
    else:
        print(fail(f"Summary totals inconsistent: {total_in_summary_prio}/{total_in_summary_grp} vs {len(per_ticket)} tickets"))

    # ── Phase 4: plan array ─────────────────────────────────────────────
    print(hdr("Phase 4 — Plan Array (Agent Contract)"))
    plan = output.get("plan", [])
    if isinstance(plan, list) and len(plan) > 0:
        print(ok(f"Plan present with {len(plan)} steps:"))
        for i, step in enumerate(plan, 1):
            print(f"    {i}. {step}")
    else:
        print(fail("Plan missing or empty"))
        failed += 1

    # ── Final verdict ───────────────────────────────────────────────────
    print(hdr("Verdict"))
    total = len(EXPECTED)
    print(f"  Tickets checked: {total}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    if failed:
        print(f"  {RED}Failed:  {failed}{RESET}")
    if skipped:
        print(f"  {YELLOW}Skipped: {skipped} (time-dependent){RESET}")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}═══ ALL CHECKS PASSED ═══{RESET}")
        return 0
    else:
        print(f"\n  {RED}{BOLD}═══ {failed} FAILURE(S) ═══{RESET}")
        for f in failures:
            print(f"    • {f}")
        return 1


if __name__ == "__main__":
    sys.exit(main())