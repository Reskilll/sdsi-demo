"""Tests for sla_engine — run with: python -m pytest test_sla_engine.py -v"""

from datetime import date, datetime, time
from sla_engine import (
    add_business_minutes,
    build_active_intervals,
    business_minutes_in_interval,
    compute_summary,
    compute_ticket,
    is_business_day,
)

# ── Test data ──────────────────────────────────────────────────────────

SLA = {"P1": {"target_hours": 4}, "P2": {"target_hours": 8}, "P3": {"target_hours": 24}, "P4": {"target_hours": 72}}
HOLIDAYS = {date(2026, 10, 22)}  # Thursday
NOW = datetime(2026, 10, 27, 16, 0, 0)

# ── M1: SLA targets ────────────────────────────────────────────────────

def test_target_minutes_mapped_correctly():
    t = compute_ticket(
        {"ticket_id": "X", "priority": "P1", "assignee_group": "G", "created_at": "2026-10-20T09:00:00",
         "status_history": [{"status": "OPEN", "timestamp": "2026-10-20T09:00:00"},
                            {"status": "RESOLVED", "timestamp": "2026-10-20T09:30:00"}]},
        SLA, HOLIDAYS, NOW)
    assert t["target_minutes"] == 240  # 4h * 60

# ── M2: Holidays excluded ──────────────────────────────────────────────

def test_business_day_rejects_weekend():
    assert not is_business_day(date(2026, 10, 24), HOLIDAYS)  # Saturday
    assert not is_business_day(date(2026, 10, 25), HOLIDAYS)  # Sunday

def test_business_day_rejects_holiday():
    assert not is_business_day(date(2026, 10, 22), HOLIDAYS)  # holiday

def test_holiday_excluded_from_business_minutes():
    mins = business_minutes_in_interval(
        datetime(2026, 10, 22, 9, 0),
        datetime(2026, 10, 22, 18, 0),
        HOLIDAYS,
    )
    assert mins == 0.0

# ── M3: ON_HOLD pauses clock ───────────────────────────────────────────

def test_on_hold_excluded_from_active_intervals():
    intervals = build_active_intervals(
        [
            {"status": "OPEN", "timestamp": "2026-10-20T10:00:00"},
            {"status": "ON_HOLD", "timestamp": "2026-10-20T11:00:00"},
            {"status": "IN_PROGRESS", "timestamp": "2026-10-21T09:00:00"},
            {"status": "RESOLVED", "timestamp": "2026-10-21T15:30:00"},
        ],
        datetime(2026, 10, 21, 15, 30),
    )
    assert intervals == [
        (datetime(2026, 10, 20, 10, 0), datetime(2026, 10, 20, 11, 0)),
        (datetime(2026, 10, 21, 9, 0), datetime(2026, 10, 21, 15, 30)),
    ]

def test_on_hold_over_holiday_is_excluded():
    """TKT-004: ON_HOLD Mon 17:00→Thu 09:30 (Thu=holiday). Active time = 60 min."""
    t = compute_ticket(
        {"ticket_id": "TKT-004", "priority": "P2", "assignee_group": "Database",
         "created_at": "2026-10-20T16:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-20T16:00:00"},
             {"status": "ON_HOLD", "timestamp": "2026-10-20T17:00:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-22T09:30:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-22T12:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 60.0  # only Mon 16:00-17:00
    assert t["breach"] is False

# ── M4: Per-ticket output shape ────────────────────────────────────────

def test_ticket_output_has_required_fields():
    t = compute_ticket(
        {"ticket_id": "TKT-001", "priority": "P1", "assignee_group": "N",
         "created_at": "2026-10-20T09:30:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-20T09:30:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-20T13:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    for k in ("ticket_id", "priority", "assignee_group", "elapsed_business_minutes",
              "due_by", "breach", "breach_minutes"):
        assert k in t, f"Missing field: {k}"

def test_tkt001_no_breach():
    """Created 09:30, resolved 13:00 same day. 3.5h < 4h → no breach."""
    t = compute_ticket(
        {"ticket_id": "TKT-001", "priority": "P1", "assignee_group": "Network",
         "created_at": "2026-10-20T09:30:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-20T09:30:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-20T10:00:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-20T13:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 210.0
    assert t["breach"] is False
    assert t["breach_minutes"] == 0.0
    assert datetime.fromisoformat(t["due_by"]) == datetime(2026, 10, 20, 13, 30)

def test_tkt002_breach_with_on_hold():
    """P1, 10:00 start, ON_HOLD 11:00→Tue 09:00, resolved 15:30. 450 active min > 240."""
    t = compute_ticket(
        {"ticket_id": "TKT-002", "priority": "P1", "assignee_group": "Network",
         "created_at": "2026-10-20T10:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-20T10:00:00"},
             {"status": "ON_HOLD", "timestamp": "2026-10-20T11:00:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-21T09:00:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-21T15:30:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 450.0  # 60 + 390
    assert t["breach"] is True
    assert t["breach_minutes"] == 210.0  # 450 - 240

def test_tkt003_p2_breach():
    """P2, created Mon 14:00, resolved Tue 17:00. 12h > 8h → breach."""
    t = compute_ticket(
        {"ticket_id": "TKT-003", "priority": "P2", "assignee_group": "Security",
         "created_at": "2026-10-19T14:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-19T14:00:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-19T15:00:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-20T17:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 720.0  # Mon 14-18 (240) + Tue 09-17 (480)
    assert t["breach"] is True
    assert t["breach_minutes"] == 240.0

def test_tkt005_p3_breach_over_holiday():
    """P3, Mon 09:00→Thu 11:00, holiday Thu → 27 active h > 24h → breach."""
    t = compute_ticket(
        {"ticket_id": "TKT-005", "priority": "P3", "assignee_group": "Database",
         "created_at": "2026-10-19T09:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-19T09:00:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-19T10:00:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-22T11:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 1620.0  # 3 full days (Mon/Tue/Wed) + Thu=0
    assert t["breach"] is True
    assert t["breach_minutes"] == 180.0  # 1620 - 1440

def test_tkt007_p4_no_breach():
    """P4, 10 days span, only 58h active < 72h → no breach."""
    t = compute_ticket(
        {"ticket_id": "TKT-007", "priority": "P4", "assignee_group": "Application",
         "created_at": "2026-10-16T10:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-16T10:00:00"},
             {"status": "RESOLVED", "timestamp": "2026-10-27T14:00:00"},
         ]},
        SLA, HOLIDAYS, NOW)
    assert t["elapsed_business_minutes"] == 3480.0  # 8h+9h+9h+9h+0h+9h+9h+5h = 58h
    assert t["breach"] is False

# ── M5: Summary ────────────────────────────────────────────────────────

def test_summary_breach_percentages():
    results = [
        {"ticket_id": "A", "priority": "P1", "assignee_group": "N", "breach": True},
        {"ticket_id": "B", "priority": "P1", "assignee_group": "N", "breach": True},
        {"ticket_id": "C", "priority": "P1", "assignee_group": "S", "breach": False},
        {"ticket_id": "D", "priority": "P2", "assignee_group": "N", "breach": False},
    ]
    s = compute_summary(results)
    assert s["by_priority"]["P1"]["breach_pct"] == 66.7  # 2/3
    assert s["by_priority"]["P2"]["breach_pct"] == 0.0
    assert s["by_assignee_group"]["N"]["breach_pct"] == 66.7   # 2/3
    assert s["by_assignee_group"]["S"]["breach_pct"] == 0.0    # 0/1

# ── Edge cases ─────────────────────────────────────────────────────────

def test_before_business_hours():
    """Minutes before 09:00 don't count."""
    mins = business_minutes_in_interval(
        datetime(2026, 10, 20, 7, 0),
        datetime(2026, 10, 20, 10, 0),
        HOLIDAYS,
    )
    assert mins == 60.0  # 09:00→10:00 only

def test_add_business_minutes_across_weekend():
    """Adding minutes that span a weekend lands on Monday."""
    result = add_business_minutes(
        datetime(2026, 10, 23, 17, 0),  # Friday
        120.0,  # 2 hours
        HOLIDAYS,
    )
    assert result.date() == date(2026, 10, 26)  # Monday
    assert result.hour == 11  # 09:00 + 2h

def test_add_business_minutes_skips_holiday():
    """Adding minutes that span a holiday skips it."""
    result = add_business_minutes(
        datetime(2026, 10, 21, 17, 0),  # Wednesday
        240.0,  # 4 hours → 1h Wed + 3h next business day (Fri, skipping Thu holiday)
        HOLIDAYS,
    )
    assert result.date() == date(2026, 10, 23)  # Friday
    assert result.hour == 12  # 09:00 + 3h

def test_no_on_hold_still_open():
    """Ticket open, never ON_HOLD, never resolved → interval extends to now."""
    t = compute_ticket(
        {"ticket_id": "O", "priority": "P3", "assignee_group": "G",
         "created_at": "2026-10-27T09:00:00",
         "status_history": [
             {"status": "OPEN", "timestamp": "2026-10-27T09:00:00"},
             {"status": "IN_PROGRESS", "timestamp": "2026-10-27T09:30:00"},
         ]},
        SLA, HOLIDAYS, datetime(2026, 10, 27, 12, 0, 0),
    )
    assert t["elapsed_business_minutes"] == 180.0  # 09:00→12:00
    assert t["breach"] is False  # 3h < 24h

def test_reentrant_on_hold():
    """Multiple ON_HOLD periods (TKT-006)."""
    intervals = build_active_intervals(
        [
            {"status": "OPEN", "timestamp": "2026-10-21T08:30:00"},
            {"status": "IN_PROGRESS", "timestamp": "2026-10-21T09:00:00"},
            {"status": "ON_HOLD", "timestamp": "2026-10-21T14:00:00"},
            {"status": "IN_PROGRESS", "timestamp": "2026-10-24T09:00:00"},
            {"status": "ON_HOLD", "timestamp": "2026-10-24T15:00:00"},
            {"status": "IN_PROGRESS", "timestamp": "2026-10-27T09:30:00"},
        ],
        None,  # not resolved
    )
    # 3 active intervals, last extends to ~now (via None)
    assert len(intervals) == 3
    # First: Wed 08:30 → Wed 14:00
    assert intervals[0] == (datetime(2026, 10, 21, 8, 30), datetime(2026, 10, 21, 14, 0))
    # Second: Sat 09:00 → Sat 15:00 (weekend, but raw timestamps kept)
    assert intervals[1] == (datetime(2026, 10, 24, 9, 0), datetime(2026, 10, 24, 15, 0))
    # Third: Tue 09:30 → now
    assert intervals[2][0] == datetime(2026, 10, 27, 9, 30)