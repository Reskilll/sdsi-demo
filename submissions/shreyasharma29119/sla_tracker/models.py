"""Data models for the SLA Tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class StatusEntry:
    """A single status change in a ticket's history."""
    status: str
    at: datetime


@dataclass
class Ticket:
    """A support ticket."""
    id: str
    priority: str
    assignee_group: str
    created: datetime
    resolved: Optional[datetime] = None
    status_history: list[StatusEntry] = field(default_factory=list)


@dataclass
class SlaPolicy:
    """SLA policy: target business hours per priority, plus business-hours window."""
    targets: dict[str, int]  # priority → target business minutes
    business_days: set[int]  # 0=Mon … 6=Sun
    business_start: str      # "HH:MM"
    business_end: str        # "HH:MM"


@dataclass(frozen=True)
class TicketSlaResult:
    """Per-ticket SLA computation result."""
    ticket_id: str
    priority: str
    assignee_group: str
    elapsed_business_minutes: int
    target_minutes: int
    due_by: datetime
    breached: bool
    breach_minutes: int