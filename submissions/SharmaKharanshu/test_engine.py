"""
Tests for SLA Engine — covers M1–M5 and edge cases.
Run:  python -m pytest test_engine.py -v
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from engine import SLAEngine

DATA = Path(__file__).parent / "data"

@pytest.fixture
def engine():
    with open(DATA / "sla_policy.json") as f:
        policy = json.load(f)
    with open(DATA / "holidays.json") as f:
        holidays = json.load(f)
    return SLAEngine(policy, holidays)


# ---- M1: SLA targets ---------------------------------------------------
def test_sla_targets(engine):
    assert engine.targets["P1"] == 240
    assert engine.targets["P2"] == 480
    assert engine.targets["P3"] == 1440
    assert engine.targets["P4"] == 4320


def test_business_minutes_same_day(engine):
    t1 = datetime(2026, 10, 26, 9, 0)   # Monday
    t2 = datetime(2026, 10, 26, 13, 30)
    assert engine._business_minutes_between(t1, t2) == 270  # 4.5 hours


def test_business_minutes_overnight(engine):
    t1 = datetime(2026, 10, 26, 17, 0)
    t2 = datetime(2026, 10, 27, 10, 0)
    # Mon: 17-18 = 60 min; Tue: 9-10 = 60 min = 120 total
    assert engine._business_minutes_between(t1, t2) == 120


def test_business_minutes_weekend_skipped(engine):
    t1 = datetime(2026, 10, 30, 17, 0)  # Friday
    t2 = datetime(2026, 11, 2, 10, 0)    # Monday
    # Fri: 17-18 = 60; Mon: 9-10 = 60 = 120
    assert engine._business_minutes_between(t1, t2) == 120


# ---- M2: Holidays excluded ----------------------------------------------
def test_holiday_excluded(engine):
    # 2026-10-28 is a holiday
    t1 = datetime(2026, 10, 27, 17, 0)  # Tuesday
    t2 = datetime(2026, 10, 29, 10, 0)   # Thursday
    # Tue: 17-18 = 60; Wed (holiday) = 0; Thu: 9-10 = 60 = 120
    assert engine._business_minutes_between(t1, t2) == 120


# ---- M3: ON_HOLD pauses clock -------------------------------------------
def test_on_hold_pauses_clock(engine):
    ticket = {
        "id": "T-ONHOLD",
        "priority": "P2",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": "2026-10-26T17:00:00",
        "status_history": [
            {"status": "OPEN", "changed_at": "2026-10-26T09:00:00"},
            {"status": "ON_HOLD", "changed_at": "2026-10-26T12:00:00"},
            {"status": "IN_PROGRESS", "changed_at": "2026-10-26T14:00:00"},
            {"status": "RESOLVED", "changed_at": "2026-10-26T17:00:00"},
        ],
    }
    r = engine.compute(ticket)
    # Active: 9-12 (180 min) + 14-17 (180 min) = 360 min
    # ON_HOLD 12-14 excluded
    assert r["elapsed_business_minutes"] == 360


def test_multiple_hold_periods(engine):
    ticket = {
        "id": "T-MULTI-HOLD",
        "priority": "P2",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": "2026-10-26T18:00:00",
        "status_history": [
            {"status": "OPEN", "changed_at": "2026-10-26T09:00:00"},
            {"status": "ON_HOLD", "changed_at": "2026-10-26T10:00:00"},
            {"status": "IN_PROGRESS", "changed_at": "2026-10-26T11:00:00"},
            {"status": "ON_HOLD", "changed_at": "2026-10-26T14:00:00"},
            {"status": "IN_PROGRESS", "changed_at": "2026-10-26T15:00:00"},
            {"status": "RESOLVED", "changed_at": "2026-10-26T18:00:00"},
        ],
    }
    r = engine.compute(ticket)
    # 9-10 (60) + 11-14 (180) + 15-18 (180) = 420
    assert r["elapsed_business_minutes"] == 420


# ---- Edge cases ---------------------------------------------------------

def test_unresolved_ticket_uses_now(engine):
    ticket = {
        "id": "T-OPEN",
        "priority": "P3",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": None,
        "status_history": [
            {"status": "OPEN", "changed_at": "2026-10-26T09:00:00"},
        ],
    }
    now = datetime(2026, 10, 26, 12, 0)
    r = engine.compute(ticket, now=now)
    assert r["elapsed_business_minutes"] == 180
    assert not r["resolved"]


def test_created_outside_business_hours(engine):
    ticket = {
        "id": "T-EARLY",
        "priority": "P1",
        "assignee_group": "Test",
        "created_at": "2026-10-26T06:00:00",
        "resolved_at": "2026-10-26T10:00:00",
        "status_history": [
            {"status": "OPEN", "changed_at": "2026-10-26T06:00:00"},
            {"status": "RESOLVED", "changed_at": "2026-10-26T10:00:00"},
        ],
    }
    r = engine.compute(ticket)
    # 6am is before 9am, clock should start at 9, so 9-10 = 60 min
    assert r["elapsed_business_minutes"] == 60


def test_invalid_priority_raises(engine):
    ticket = {
        "id": "T-BAD",
        "priority": "P5",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": None,
        "status_history": [{"status": "OPEN", "changed_at": "2026-10-26T09:00:00"}],
    }
    with pytest.raises(ValueError, match="Unknown priority"):
        engine.compute(ticket)


def test_empty_status_history(engine):
    ticket = {
        "id": "T-EMPTY",
        "priority": "P3",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": "2026-10-26T10:00:00",
        "status_history": [],
    }
    r = engine.compute(ticket)
    assert r["elapsed_business_minutes"] == 0  # no active periods


def test_due_by_projection(engine):
    # P1 = 4h = 240 minutes from 09:00 on a Monday = 13:00 same day
    ticket = {
        "id": "T-DUE",
        "priority": "P1",
        "assignee_group": "Test",
        "created_at": "2026-10-26T09:00:00",
        "resolved_at": None,
        "status_history": [{"status": "OPEN", "changed_at": "2026-10-26T09:00:00"}],
    }
    r = engine.compute(ticket, now=datetime(2026, 10, 26, 12, 0))
    due = datetime.fromisoformat(r["due_by"])
    assert due == datetime(2026, 10, 26, 13, 0)


def test_summary(engine):
    reports = [
        {"ticket_id": "A", "priority": "P1", "assignee_group": "Network", "breach": True},
        {"ticket_id": "B", "priority": "P1", "assignee_group": "Network", "breach": False},
        {"ticket_id": "C", "priority": "P2", "assignee_group": "Security", "breach": True},
    ]
    s = engine.summary(reports)
    assert s["by_priority"]["P1"]["breach_pct"] == 50.0
    assert s["by_priority"]["P2"]["breach_pct"] == 100.0
    assert s["by_assignee_group"]["Network"]["breach_pct"] == 50.0
    assert s["by_assignee_group"]["Security"]["breach_pct"] == 100.0