"""Core expense splitting and debt simplification engine."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ExpenseError(Exception):
    """Validation error for an expense or group operation."""


class SplitType(Enum):
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"


@dataclass
class Settlement:
    from_member: str
    to_member: str
    amount: Decimal

    def __str__(self) -> str:
        return f"{self.from_member} pays {self.to_member} ₹{self.amount:.2f}"


@dataclass
class Expense:
    title: str
    total: Decimal
    paid_by: str
    split_type: SplitType
    shares: List[Dict[str, Any]]  # [{"member": str, "amount"?: Decimal, "percentage"?: Decimal}]

    @classmethod
    def from_dict(cls, d: dict) -> "Expense":
        """Build an Expense from a parsed-JSON dict (str amounts → Decimal)."""
        total = _to_decimal(d["total"])
        split = d["split"]
        st = SplitType(split["type"])
        shares: List[Dict[str, Any]] = []
        if st == SplitType.EQUAL:
            for m in split["members"]:
                shares.append({"member": m})
        elif st == SplitType.EXACT:
            for s in split["shares"]:
                shares.append({"member": s["member"], "amount": _to_decimal(s["amount"])})
        elif st == SplitType.PERCENTAGE:
            for s in split["shares"]:
                shares.append({"member": s["member"], "percentage": _to_decimal(s.get("percentage", s.get("percent", 0)))})
        return cls(title=d["title"], total=total, paid_by=d["paid_by"],
                   split_type=st, shares=shares)


def _to_decimal(v: Any) -> Decimal:
    """Safely convert int/float/str/Decimal to Decimal."""
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ---------------------------------------------------------------------------
# Splitter engine
# ---------------------------------------------------------------------------

class ExpenseSplitter:
    """Manage a group's expenses and compute net balances / simplified debts."""

    def __init__(self, members: Optional[List[str]] = None):
        self._members: List[str] = []
        self.expenses: List[Expense] = []
        if members:
            for m in members:
                self._add_member(m)

    # -- members ------------------------------------------------------------

    @property
    def members(self) -> List[str]:
        return list(self._members)

    def _add_member(self, name: str) -> None:
        if name not in self._members:
            self._members.append(name)

    # -- add expense --------------------------------------------------------

    def add_expense(self, expense: Expense) -> None:
        """Validate and record an expense."""
        self._validate(expense)
        for s in expense.shares:
            self._add_member(s["member"])
        self._add_member(expense.paid_by)
        self.expenses.append(expense)

    def _validate(self, e: Expense) -> None:
        if e.total <= 0:
            raise ExpenseError("Total must be positive")
        if not e.title:
            raise ExpenseError("Expense must have a title")
        if not e.paid_by:
            raise ExpenseError("Payer not specified")
        if not e.shares:
            raise ExpenseError("At least one share required")

        if e.split_type == SplitType.EQUAL:
            if not e.shares:
                raise ExpenseError("Equal split needs at least one member")
            # payer must be among the members sharing
            shared_members = {s["member"] for s in e.shares}
            if e.paid_by not in shared_members:
                raise ExpenseError(f"Payer '{e.paid_by}' must be among the equal-split members")

        elif e.split_type == SplitType.EXACT:
            total = Decimal("0")
            for s in e.shares:
                if "amount" not in s or s["amount"] is None:
                    raise ExpenseError("Exact split requires an amount for each share")
                total += s["amount"]
            if total != e.total:
                raise ExpenseError(
                    f"Exact amounts sum to ₹{total:.2f}, expected ₹{e.total:.2f}")
            shared_members = {s["member"] for s in e.shares}
            if e.paid_by not in shared_members:
                raise ExpenseError(f"Payer '{e.paid_by}' is not in the exact-split shares")

        elif e.split_type == SplitType.PERCENTAGE:
            pct_total = Decimal("0")
            for s in e.shares:
                pct = s.get("percentage", Decimal("0"))
                pct_total += pct
            if pct_total != Decimal("100"):
                raise ExpenseError(f"Percentages sum to {pct_total}, expected 100")
            shared_members = {s["member"] for s in e.shares}
            if e.paid_by not in shared_members:
                raise ExpenseError(f"Payer '{e.paid_by}' is not in the percentage-split members")

    # -- net balances -------------------------------------------------------

    def net_balances(self) -> Dict[str, Decimal]:
        """Return {member: net_amount} where positive = is owed money."""
        balances: Dict[str, Decimal] = {m: Decimal("0") for m in self._members}

        for e in self.expenses:
            shares = self._compute_shares(e)
            # payer is credited the total (they fronted the money)
            balances[e.paid_by] += e.total
            # each member (including payer) owes their share
            for member, amount in shares:
                balances[member] -= amount

        return balances

    def _compute_shares(self, e: Expense) -> List[Tuple[str, Decimal]]:
        """Return [(member, owed_amount)] for this expense."""
        result: List[Tuple[str, Decimal]] = []

        if e.split_type == SplitType.EQUAL:
            count = len(e.shares)
            per_person = e.total / Decimal(str(count))
            # distribute rounding remainder (paise) to first members
            # Using quantize to get base floor, then distribute remainder
            base = per_person.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            allocated = base * count
            remainder = (e.total - allocated).quantize(Decimal("0.01"))
            # distribute remainder cents (should be < count)
            for i, s in enumerate(e.shares):
                amt = base
                if remainder > 0:
                    amt += Decimal("0.01")
                    remainder -= Decimal("0.01")
                elif remainder < 0:
                    amt -= Decimal("0.01")
                    remainder += Decimal("0.01")
                result.append((s["member"] if isinstance(s, dict) else s, amt))
        elif e.split_type == SplitType.EXACT:
            for s in e.shares:
                result.append((s["member"], s["amount"]))
        elif e.split_type == SplitType.PERCENTAGE:
            allocated = Decimal("0")
            for i, s in enumerate(e.shares):
                pct = s["percentage"]
                raw = (e.total * pct / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
                # Round to nearest paisa; handle last-share remainder
                result.append((s["member"], raw))
                allocated += raw
            # Distribute any fractional remainder to the largest share
            remainder = (e.total - allocated).quantize(Decimal("0.01"))
            if remainder != 0:
                # find the share with the largest absolute percentage
                max_idx = max(range(len(e.shares)),
                              key=lambda i: e.shares[i].get("percentage", Decimal("0")))
                mem, amt = result[max_idx]
                result[max_idx] = (mem, amt + remainder)

        return result

    # -- debt simplification ------------------------------------------------

    def simplify(self) -> List[Settlement]:
        """
        Reduce debts to minimum number of transactions (greedy optimal for
        single-currency: max-debtor pays max-creditor).
        """
        net = self.net_balances()
        # debtors = people who owe money (negative balance → positive amount owed)
        debtors: List[Tuple[str, Decimal]] = [
            (m, -bal) for m, bal in net.items() if bal < 0
        ]
        creditors: List[Tuple[str, Decimal]] = [
            (m, bal) for m, bal in net.items() if bal > 0
        ]
        # Sort descending so largest is settled first
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        settlements: List[Settlement] = []
        i = j = 0
        while i < len(debtors) and j < len(creditors):
            amt = min(debtors[i][1], creditors[j][1])
            amt = amt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if amt > 0:
                settlements.append(Settlement(
                    from_member=debtors[i][0],
                    to_member=creditors[j][0],
                    amount=amt,
                ))
            debtors[i] = (debtors[i][0], debtors[i][1] - amt)
            creditors[j] = (creditors[j][0], creditors[j][1] - amt)
            if debtors[i][1] == 0:
                i += 1
            if creditors[j][1] == 0:
                j += 1

        return settlements

    # -- batch input --------------------------------------------------------

    @classmethod
    def from_json(cls, path: str) -> "ExpenseSplitter":
        """Build a splitter from a JSON file path."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        members = data.get("members", [])
        splitter = cls(members=members)
        for ed in data.get("expenses", []):
            splitter.add_expense(Expense.from_dict(ed))
        return splitter

    @classmethod
    def from_dict(cls, data: dict) -> "ExpenseSplitter":
        """Build a splitter from a dict (parsed JSON)."""
        members = data.get("members", [])
        splitter = cls(members=members)
        for ed in data.get("expenses", []):
            splitter.add_expense(Expense.from_dict(ed))
        return splitter

    # -- report -------------------------------------------------------------

    def report(self) -> str:
        """Human-readable summary of balances and settlements."""
        lines = ["=== Expense Splitter Report ===\n"]

        # Expenses
        lines.append("Expenses:")
        for e in self.expenses:
            lines.append(f"  • {e.title}: ₹{e.total:.2f} paid by {e.paid_by} ({e.split_type.value})")
            shares = self._compute_shares(e)
            for member, amt in shares:
                lines.append(f"      {member} owes ₹{amt:.2f}")
        lines.append("")

        # Balances
        lines.append("Net Balances:")
        net = self.net_balances()
        for member in self.members:
            bal = net.get(member, Decimal("0"))
            sign = "+" if bal >= 0 else ""
            lines.append(f"  {member}: {sign}₹{bal:.2f}")
        lines.append("")

        # Settlements
        lines.append("Settlements (simplified):")
        settlements = self.simplify()
        if not settlements:
            lines.append("  All settled up!")
        else:
            for s in settlements:
                lines.append(f"  • {s}")
        lines.append("")

        return "\n".join(lines)