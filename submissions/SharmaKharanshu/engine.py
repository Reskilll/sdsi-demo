"""
SLA Engine — pure business logic, no framework dependencies.
Calculates elapsed business minutes, due-by time, and breach status.
"""

from datetime import datetime, timedelta, date
from typing import Optional

BUSINESS_START = 9   # 09:00
BUSINESS_END   = 18  # 18:00


class SLAEngine:
    """Stateless SLA calculator. Pass policy + holidays once, reuse across tickets."""

    def __init__(self, sla_policy: dict, holidays: list[str]):
        self.targets: dict[str, int] = {
            p: int(d["sla_minutes"])
            for p, d in sla_policy["priorities"].items()
        }
        self.holiday_set: set[date] = {date.fromisoformat(h) for h in holidays}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def compute(self, ticket: dict, now: Optional[datetime] = None) -> dict:
        """Return full SLA report for one ticket."""
        if now is None:
            now = datetime.now()

        priority = ticket["priority"].upper()
        sla_target = self.targets.get(priority)
        if sla_target is None:
            raise ValueError(f"Unknown priority: {priority}")

        status_history = sorted(ticket["status_history"], key=lambda e: e["changed_at"])
        created_at = datetime.fromisoformat(ticket["created_at"])
        resolved_at = (
            datetime.fromisoformat(ticket["resolved_at"])
            if ticket.get("resolved_at")
            else None
        )

        elapsed = self._calc_elapsed(status_history, created_at, resolved_at, now)
        due_by  = self._add_business_minutes(created_at, sla_target)
        breach  = elapsed > sla_target
        breach_minutes = max(0, elapsed - sla_target) if breach else 0

        return {
            "ticket_id": ticket["id"],
            "priority": priority,
            "assignee_group": ticket["assignee_group"],
            "sla_target_minutes": sla_target,
            "elapsed_business_minutes": elapsed,
            "due_by": due_by.isoformat(),
            "breach": breach,
            "breach_minutes": breach_minutes,
            "resolved": resolved_at is not None,
            "on_hold_periods": self._count_holds(status_history),
        }

    def summary(self, reports: list[dict]) -> dict:
        """M5: breach % per priority and per assignee group."""
        by_priority: dict[str, dict] = {}
        by_group: dict[str, dict] = {}

        for r in reports:
            p = r["priority"]
            g = r["assignee_group"]

            by_priority.setdefault(p, {"total": 0, "breached": 0})
            by_group.setdefault(g, {"total": 0, "breached": 0})

            by_priority[p]["total"] += 1
            by_group[g]["total"] += 1
            if r["breach"]:
                by_priority[p]["breached"] += 1
                by_group[g]["breached"] += 1

        def pct(d: dict) -> dict:
            return {
                k: {
                    "total": v["total"],
                    "breached": v["breached"],
                    "breach_pct": round(v["breached"] / v["total"] * 100, 1),
                }
                for k, v in d.items()
            }

        return {"by_priority": pct(by_priority), "by_assignee_group": pct(by_group)}

    # ------------------------------------------------------------------
    # business-minute arithmetic
    # ------------------------------------------------------------------

    def _is_business_day(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self.holiday_set

    def _next_business_moment(self, dt: datetime) -> datetime:
        """Snap dt forward to the next business-minute boundary."""
        d = dt.date()
        if not self._is_business_day(d):
            # jump to next business day 09:00
            d = self._next_business_day(d)
            return datetime(d.year, d.month, d.day, BUSINESS_START, 0)
        if dt.hour < BUSINESS_START:
            return dt.replace(hour=BUSINESS_START, minute=0, second=0, microsecond=0)
        if dt.hour >= BUSINESS_END:
            d = self._next_business_day(d)
            return datetime(d.year, d.month, d.day, BUSINESS_START, 0)
        return dt

    def _next_business_day(self, d: date) -> date:
        d += timedelta(days=1)
        while not self._is_business_day(d):
            d += timedelta(days=1)
        return d

    def _business_minutes_between(self, start: datetime, end: datetime) -> int:
        """Count business minutes in [start, end)."""
        if start >= end:
            return 0
        total = 0
        current = start
        while current < end:
            current = self._next_business_moment(current)
            if current >= end:
                break
            day_end = current.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
            chunk_end = min(day_end, end)
            if chunk_end > current:
                total += int((chunk_end - current).total_seconds() // 60)
            current = day_end
            # advance to next business day automatically on next loop iteration
        return total

    def _add_business_minutes(self, start: datetime, minutes: int) -> datetime:
        """Project `minutes` business-minutes forward from `start`."""
        current = start
        remaining = minutes
        while remaining > 0:
            current = self._next_business_moment(current)
            day_end = current.replace(hour=BUSINESS_END, minute=0, second=0, microsecond=0)
            available = int((day_end - current).total_seconds() // 60)
            if remaining <= available:
                return current + timedelta(minutes=remaining)
            remaining -= available
            current = day_end
        return current

    # ------------------------------------------------------------------
    # status-history parsing
    # ------------------------------------------------------------------

    def _calc_elapsed(
        self,
        status_history: list[dict],
        created_at: datetime,
        resolved_at: Optional[datetime],
        now: datetime,
    ) -> int:
        end_marker = resolved_at or now

        # Build active intervals — clock runs when status != ON_HOLD
        active_periods: list[tuple[datetime, datetime]] = []
        for i, entry in enumerate(status_history):
            t0 = datetime.fromisoformat(entry["changed_at"])
            t1 = (
                datetime.fromisoformat(status_history[i + 1]["changed_at"])
                if i + 1 < len(status_history)
                else end_marker
            )
            if entry["status"].upper() != "ON_HOLD":
                active_periods.append((t0, t1))

        # Sum business minutes across all active periods
        total = 0
        for t0, t1 in active_periods:
            total += self._business_minutes_between(t0, t1)
        return total

    @staticmethod
    def _count_holds(status_history: list[dict]) -> int:
        return sum(1 for e in status_history if e["status"].upper() == "ON_HOLD")