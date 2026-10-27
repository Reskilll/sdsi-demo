"""Immutable domain models and error types for the SLA tracker.

All datetimes held by these models are *naive* and expressed in the policy's
local wall-clock time. Timezone conversion happens only at the I/O boundary
(see ``timeutil``), which keeps business-hours arithmetic simple and DST-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, tzinfo
from typing import Mapping

#: Status a ticket is implicitly in between ``created_at`` and its first event.
INITIAL_STATUS = "NEW"

RUNNING = "RUNNING"
PAUSED = "PAUSED"
STOPPED = "STOPPED"


class SlaError(Exception):
    """Base error. Messages are safe to show to end users (no internals)."""


class ConfigError(SlaError):
    """Fatal problem with an input file or configuration value."""


@dataclass(frozen=True)
class StatusEvent:
    status: str
    at: datetime


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    priority: str
    assignee_group: str
    created_at: datetime
    history: tuple[StatusEvent, ...] = ()


@dataclass(frozen=True)
class SlaPolicy:
    timezone: tzinfo
    timezone_name: str
    day_start: time
    day_end: time
    working_days: frozenset[int]
    targets_minutes: Mapping[str, int]
    running_statuses: frozenset[str]
    paused_statuses: frozenset[str]
    stopped_statuses: frozenset[str]
    at_risk_ratio: float = 0.8

    @property
    def known_statuses(self) -> frozenset[str]:
        return self.running_statuses | self.paused_statuses | self.stopped_statuses

    def classify(self, status: str) -> str:
        """Map a ticket status to the SLA clock state it implies."""
        if status in self.running_statuses:
            return RUNNING
        if status in self.paused_statuses:
            return PAUSED
        if status in self.stopped_statuses:
            return STOPPED
        raise KeyError(status)


@dataclass(frozen=True)
class TicketError:
    """A ticket that failed validation; reported, never silently dropped."""

    ticket_ref: str
    message: str

    def to_dict(self) -> dict:
        return {"ticket": self.ticket_ref, "error": self.message}


def _minutes(seconds: int) -> int | float:
    return seconds // 60 if seconds % 60 == 0 else round(seconds / 60, 2)


@dataclass(frozen=True)
class TicketResult:
    ticket_id: str
    priority: str
    assignee_group: str
    current_status: str
    clock_state: str
    target_seconds: int
    elapsed_seconds: int
    paused_seconds: int
    due_by: datetime
    at_risk: bool

    @property
    def breached(self) -> bool:
        return self.elapsed_seconds > self.target_seconds

    @property
    def breach_seconds(self) -> int:
        return max(0, self.elapsed_seconds - self.target_seconds)

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.target_seconds - self.elapsed_seconds)

    @property
    def is_open(self) -> bool:
        return self.clock_state != STOPPED

    def to_dict(self, tz: tzinfo) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "priority": self.priority,
            "assignee_group": self.assignee_group,
            "current_status": self.current_status,
            "clock_state": self.clock_state,
            "target_minutes": _minutes(self.target_seconds),
            "elapsed_business_minutes": _minutes(self.elapsed_seconds),
            "on_hold_business_minutes": _minutes(self.paused_seconds),
            "remaining_minutes": _minutes(self.remaining_seconds),
            "due_by": self.due_by.replace(tzinfo=tz).isoformat(),
            "breached": self.breached,
            "breach_minutes": _minutes(self.breach_seconds),
            "at_risk": self.at_risk,
        }

