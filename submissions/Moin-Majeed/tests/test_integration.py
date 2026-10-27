"""Integration tests — full pipeline with sample data files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sla_tracker.business_calendar import BusinessCalendar
from sla_tracker.models import SlaPolicy, Ticket
from sla_tracker.reporter import build_summary
from sla_tracker.sla_calculator import calculate_ticket_sla
from sla_tracker.validators import (
    validate_holidays,
    validate_sla_policy,
    validate_ticket,
)

DATA = Path(__file__).parent.parent / "data"
UTC = timezone.utc


def _load_data() -> tuple[list[Ticket], SlaPolicy, BusinessCalendar]:
    raw_tickets = json.loads((DATA / "tickets.json").read_text())
    raw_policy = json.loads((DATA / "sla_policy.json").read_text())
    raw_holidays = json.loads((DATA / "holidays.json").read_text())

    holidays = validate_holidays(raw_holidays)
    targets = validate_sla_policy(raw_policy)
    calendar = BusinessCalendar(holidays=holidays, tz="UTC")

    tickets = [validate_ticket(t) for t in raw_tickets]
    return tickets, SlaPolicy(targets=targets), calendar


class TestIntegration:
    def test_all_tickets_load(self) -> None:
        tickets, _, _ = _load_data()
        assert len(tickets) == 8

    def test_tkt001_no_breach(self) -> None:
        """TKT-001: created 09:00, resolved 13:00 = 240 min → no breach for P1."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-001")
        report = calculate_ticket_sla(tkt, policy, cal)
        # 09:00–13:00 = 4h = 240 min
        assert report.elapsed_business_minutes == 240.0
        assert not report.breached

    def test_tkt002_on_hold(self) -> None:
        """TKT-002: P2, created 08:00, ON_HOLD 11:00-14:00, resolved 16:30."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-002")
        report = calculate_ticket_sla(tkt, policy, cal)
        # Active: 09:00-11:00 (120) + 14:00-16:30 (150) = 270
        # P2 = 480 → no breach
        assert report.elapsed_business_minutes == 270.0
        assert not report.breached

    def test_tkt003_still_open(self) -> None:
        """TKT-003: P3, created Oct 27 09:00, still OPEN."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-003")
        ref = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        report = calculate_ticket_sla(tkt, policy, cal, ref=ref)
        # 09:00-14:00 = 300 min → no breach (P3 = 1440)
        assert report.elapsed_business_minutes == 300.0
        assert not report.breached

    def test_tkt004_crosses_weekend(self) -> None:
        """TKT-004: P1, created Fri 17:30, ON_HOLD 17:45, resumed Tue 09:15."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-004")
        ref = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        report = calculate_ticket_sla(tkt, policy, cal, ref=ref)
        # Active: Fri 17:30-17:45 (15 min) + Tue 09:15-14:00 (285 min) = 300
        # P1 = 240 → breach by 60
        assert report.elapsed_business_minutes == 300.0
        assert report.breached
        assert report.breach_minutes == 60.0

    def test_tkt005_short_p4(self) -> None:
        """TKT-005: P4, created 10:00, resolved 11:00 = 60 min. No breach."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-005")
        report = calculate_ticket_sla(tkt, policy, cal)
        assert report.elapsed_business_minutes == 60.0
        assert not report.breached

    def test_tkt006_multiple_on_hold(self) -> None:
        """TKT-006: P2, created Sunday Oct 25. Two ON_HOLD segments.

        All Sunday entries are during non-business hours.
        Active: Mon 09:00-14:00 (resolved) = 300 min. P2 = 480 → no breach.
        """
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-006")
        report = calculate_ticket_sla(tkt, policy, cal)
        assert report.elapsed_business_minutes == 300.0
        assert not report.breached

    def test_tkt007_p1_crosses_days(self) -> None:
        """TKT-007: P1, created Mon 16:00, resolved Tue 10:30."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-007")
        report = calculate_ticket_sla(tkt, policy, cal)
        # Mon: 16:00-18:00 = 120; Tue: 09:00-10:30 = 90 → 210
        # P1 = 240 → no breach
        assert report.elapsed_business_minutes == 210.0
        assert not report.breached

    def test_tkt008_created_after_hours(self) -> None:
        """TKT-008: P3, created Mon 20:00 (after hours), worked Tue 09:00-12:00."""
        tickets, policy, cal = _load_data()
        tkt = next(t for t in tickets if t.ticket_id == "TKT-008")
        report = calculate_ticket_sla(tkt, policy, cal)
        # Tue 09:00-12:00 = 180 min
        assert report.elapsed_business_minutes == 180.0
        assert not report.breached

    def test_summary_has_all_priorities(self) -> None:
        tickets, policy, cal = _load_data()
        ref = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        reports = [calculate_ticket_sla(t, policy, cal, ref=ref) for t in tickets]
        summary = build_summary(reports)
        assert summary.total_tickets == 8
        assert len(summary.by_priority) == 4
        assert len(summary.by_group) == 3  # Network, Database, Desktop
