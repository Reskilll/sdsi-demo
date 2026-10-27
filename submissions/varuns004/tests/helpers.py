"""Shared fixtures. Oct 2026: the 5th and 12th are Mondays; the 10th is a Saturday."""
from __future__ import annotations

from datetime import date, datetime, time

from sla_tracker.business_calendar import BusinessCalendar
from sla_tracker.loader import parse_policy
from sla_tracker.models import StatusEvent, Ticket

POLICY = parse_policy({"timezone": "+05:30"})


def dt(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute)


def calendar(*holidays: date) -> BusinessCalendar:
    return BusinessCalendar(time(9), time(18), frozenset(range(5)), frozenset(holidays))


def ticket(priority: str, created: datetime, *events: tuple[str, datetime],
           group: str = "G", tid: str = "T-1") -> Ticket:
    history = tuple(sorted((StatusEvent(s, at) for s, at in events), key=lambda e: e.at))
    return Ticket(tid, priority, group, created, history)

