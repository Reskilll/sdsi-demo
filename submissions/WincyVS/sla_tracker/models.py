"""Data models for SLA Tracker — strongly typed dataclasses with serialization."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import json


@dataclass
class StatusTransition:
    """A single status change event in a ticket's lifecycle."""
    timestamp: datetime
    status: str  # one of: CREATED, IN_PROGRESS, ON_HOLD, RESOLVED, CLOSED

    @staticmethod
    def from_dict(d: dict) -> "StatusTransition":
        ts = datetime.fromisoformat(d["timestamp"])
        return StatusTransition(timestamp=ts, status=d["status"].upper().strip())

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp.isoformat(), "status": self.status}


@dataclass
class Ticket:
    """A service desk ticket."""
    ticket_id: str
    priority: str  # P1, P2, P3, P4
    assignee_group: Optional[str]
    transitions: list[StatusTransition]

    def __post_init__(self):
        if not self.assignee_group:
            self.assignee_group = "Unassigned"

    @staticmethod
    def from_dict(d: dict) -> "Ticket":
        transitions = [StatusTransition.from_dict(t) for t in d.get("transitions", [])]
        transitions.sort(key=lambda t: t.timestamp)
        return Ticket(
            ticket_id=d["ticket_id"],
            priority=d.get("priority", "P4").upper().strip(),
            assignee_group=d.get("assignee_group") or "Unassigned",
            transitions=transitions,
        )

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "priority": self.priority,
            "assignee_group": self.assignee_group,
            "transitions": [t.to_dict() for t in self.transitions],
        }


@dataclass
class SLAPolicy:
    """SLA target minutes per priority and business hours definition."""
    targets: dict[str, int]  # {"P1": 240, "P2": 480, "P3": 1440, "P4": 4320}
    business_start_hour: int = 9
    business_end_hour: int = 18

    @property
    def business_minutes_per_day(self) -> int:
        return (self.business_end_hour - self.business_start_hour) * 60

    def target_minutes(self, priority: str) -> int:
        return self.targets.get(priority.upper(), self.targets.get("P4", 4320))

    @staticmethod
    def from_dict(d: dict) -> "SLAPolicy":
        return SLAPolicy(
            targets=d.get("targets", d.get("sla_targets", {})),
            business_start_hour=d.get("business_start_hour", 9),
            business_end_hour=d.get("business_end_hour", 18),
        )

    @staticmethod
    def from_file(path: str) -> "SLAPolicy":
        with open(path, "r") as f:
            return SLAPolicy.from_dict(json.load(f))


@dataclass
class TicketSLAResult:
    """Per-ticket SLA computation result."""
    ticket_id: str
    priority: str
    assignee_group: str
    sla_target_minutes: int
    elapsed_business_minutes: float
    due_by: datetime
    is_breached: bool
    breach_minutes: float
    as_of: datetime
    total_paused_minutes: float = 0.0
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "priority": self.priority,
            "assignee_group": self.assignee_group,
            "sla_target_minutes": self.sla_target_minutes,
            "elapsed_business_minutes": round(self.elapsed_business_minutes, 2),
            "due_by": self.due_by.isoformat(),
            "is_breached": self.is_breached,
            "breach_minutes": round(self.breach_minutes, 2),
            "as_of": self.as_of.isoformat(),
            "total_paused_minutes": round(self.total_paused_minutes, 2),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AnalyticsSummary:
    """Aggregated breach statistics by dimension."""
    by_priority: dict[str, dict] = field(default_factory=dict)
    by_assignee_group: dict[str, dict] = field(default_factory=dict)
    overall: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "by_priority": self.by_priority,
            "by_assignee_group": self.by_assignee_group,
            "overall": self.overall,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(dt: datetime) -> datetime:
    """Normalize datetime to UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)