"""Tests for input validation."""

from __future__ import annotations

from datetime import date

import pytest

from sla_tracker.models import Priority, TicketStatus
from sla_tracker.validators import (
    ValidationError,
    validate_holidays,
    validate_sla_policy,
    validate_ticket,
)


class TestValidateTicket:
    def test_valid_ticket(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "alice",
            "assignee_group": "Net",
            "created_at": "2026-10-26T09:00:00Z",
            "status_history": [
                {"status": "OPEN", "at": "2026-10-26T09:00:00Z"},
            ],
        }
        ticket = validate_ticket(raw)
        assert ticket.ticket_id == "T-1"
        assert ticket.priority == Priority.P1
        assert ticket.status_history[0].status == TicketStatus.OPEN

    def test_missing_key(self) -> None:
        with pytest.raises(ValidationError, match="priority"):
            validate_ticket({"ticket_id": "T", "created_at": "2026-10-26T09:00:00Z"})

    def test_invalid_priority(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 9,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "2026-10-26T09:00:00Z",
        }
        with pytest.raises(ValidationError, match="priority"):
            validate_ticket(raw)

    def test_invalid_datetime(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "not-a-date",
        }
        with pytest.raises(ValidationError, match="datetime"):
            validate_ticket(raw)

    def test_naive_datetime_treated_as_utc(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "2026-10-26T09:00:00",
        }
        ticket = validate_ticket(raw)
        assert ticket.created_at.tzinfo is not None

    def test_invalid_status(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "2026-10-26T09:00:00Z",
            "status_history": [{"status": "BOGUS", "at": "2026-10-26T09:00:00Z"}],
        }
        with pytest.raises(ValidationError, match="status"):
            validate_ticket(raw)

    def test_history_not_list(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "2026-10-26T09:00:00Z",
            "status_history": "not-a-list",
        }
        with pytest.raises(ValidationError, match="list"):
            validate_ticket(raw)

    def test_history_sorted_chronologically(self) -> None:
        raw = {
            "ticket_id": "T-1",
            "priority": 1,
            "assignee": "a",
            "assignee_group": "g",
            "created_at": "2026-10-26T09:00:00Z",
            "status_history": [
                {"status": "RESOLVED", "at": "2026-10-26T12:00:00Z"},
                {"status": "OPEN", "at": "2026-10-26T09:00:00Z"},
            ],
        }
        ticket = validate_ticket(raw)
        assert ticket.status_history[0].status == TicketStatus.OPEN
        assert ticket.status_history[1].status == TicketStatus.RESOLVED


class TestValidateSlaPolicy:
    def test_valid_policy(self) -> None:
        raw = {"P1": 240, "P2": 480, "P3": 1440, "P4": 4320}
        targets = validate_sla_policy(raw)
        assert targets[Priority.P1] == 240
        assert targets[Priority.P4] == 4320

    def test_missing_priority(self) -> None:
        raw = {"P1": 240, "P2": 480, "P3": 1440}
        with pytest.raises(ValidationError, match="P4"):
            validate_sla_policy(raw)

    def test_non_positive(self) -> None:
        raw = {"P1": 0, "P2": 480, "P3": 1440, "P4": 4320}
        with pytest.raises(ValidationError, match="positive"):
            validate_sla_policy(raw)

    def test_non_integer(self) -> None:
        raw = {"P1": "four", "P2": 480, "P3": 1440, "P4": 4320}
        with pytest.raises(ValidationError, match="integer"):
            validate_sla_policy(raw)


class TestValidateHolidays:
    def test_valid_holidays(self) -> None:
        raw = ["2026-01-01", "2026-12-25"]
        holidays = validate_holidays(raw)
        assert holidays == {date(2026, 1, 1), date(2026, 12, 25)}

    def test_not_list(self) -> None:
        with pytest.raises(ValidationError, match="array"):
            validate_holidays({"a": "b"})  # type: ignore[arg-type]

    def test_invalid_date(self) -> None:
        raw = ["2026-13-99"]
        with pytest.raises(ValidationError, match="date"):
            validate_holidays(raw)
