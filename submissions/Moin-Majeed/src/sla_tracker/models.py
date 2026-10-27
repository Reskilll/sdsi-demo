"""Core domain models for the SLA tracker.

All datetimes are stored and processed as timezone-aware UTC. The business
calendar is the only component that reasons about wall-clock time in the
support centre's local timezone.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime

# ── enums ────────────────────────────────────────────────────────────────────


class Priority(enum.IntEnum):
    """Ticket priority — the numeric value matches the SLA policy key."""

    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


class TicketStatus(str, enum.Enum):
    """Possible status values in the status-history ledger."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"
    ON_HOLD = "ON_HOLD"  # SLA clock is paused
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# ── dataclasses ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StatusEntry:
    """A single entry in the ticket's status timeline."""

    status: TicketStatus
    at: datetime  # UTC


@dataclass(frozen=True)
class Ticket:
    """A support ticket as it arrives from the input file."""

    ticket_id: str
    priority: Priority
    assignee: str
    assignee_group: str
    created_at: datetime  # UTC — when the SLA clock first ticks
    status_history: list[StatusEntry] = field(default_factory=list)


@dataclass(frozen=True)
class SlaPolicy:
    """SLA window per priority, expressed in business minutes.

    One policy is shared across all tickets; loaded from sla_policy.json.
    """

    targets: dict[Priority, int]  # priority → business-minute window


@dataclass(frozen=True)
class TicketReport:
    """Per-ticket SLA calculation result."""

    ticket_id: str
    priority: Priority
    assignee_group: str
    elapsed_business_minutes: float
    sla_target_minutes: int
    due_by: datetime  # UTC wall-clock time the SLA expires
    breached: bool
    breach_minutes: float  # 0 if not breached


@dataclass(frozen=True)
class PriorityBreachSummary:
    """Breach percentage for a single priority."""

    priority: Priority
    total: int
    breached: int
    breach_pct: float


@dataclass(frozen=True)
class GroupBreachSummary:
    """Breach percentage for a single assignee group."""

    group: str
    total: int
    breached: int
    breach_pct: float


@dataclass(frozen=True)
class SummaryReport:
    """Aggregate SLA report."""

    by_priority: list[PriorityBreachSummary]
    by_group: list[GroupBreachSummary]
    total_tickets: int
    overall_breach_pct: float
