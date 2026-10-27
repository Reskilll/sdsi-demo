"""Splitwise-lite: an expense splitter with debt simplification.

All money is handled as integer *paise* (1/100 of a rupee) so that equal
splitting, exact sums and percentage rounding stay exact with no floating
point drift. Helpers convert to/from human-readable rupee strings.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple


class ValidationError(ValueError):
    """Input failed validation; the message is safe to show to a user."""


# --------------------------------------------------------------------------- #
# Money helpers (integer paise)
# --------------------------------------------------------------------------- #

def to_paise(value: Any) -> int:
    """Parse a money value (int, float, or string) into integer paise."""
    if isinstance(value, bool):
        raise ValidationError(f"money value must be a number, got {value!r}")
    if isinstance(value, str):
        value = value.strip().replace("₹", "").replace(",", "").replace(" ", "")
        if not value:
            raise ValidationError("empty money string")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"invalid money value: {value!r}")
    if not d.is_finite():
        raise ValidationError(f"invalid money value: {value!r}")
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def format_money(paise: int) -> str:
    """Render integer paise as a rupee string, e.g. 1234 -> '₹12.34'."""
    sign = "-" if paise < 0 else ""
    rupees, p = divmod(abs(paise), 100)
    return f"{sign}₹{rupees}.{p:02d}"


def _to_percent(value: Any) -> int:
    """Parse a percentage into integer hundredths-of-a-percent (e.g. 33.33 -> 3333)."""
    if isinstance(value, bool):
        raise ValidationError(f"percentage must be a number, got {value!r}")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"invalid percentage: {value!r}")
    if not d.is_finite():
        raise ValidationError(f"invalid percentage: {value!r}")
    scaled = int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if scaled < 0:
        raise ValidationError("percentages must be non-negative")
    return scaled


# --------------------------------------------------------------------------- #
# Split computation
# --------------------------------------------------------------------------- #

def _validate_members(names: Sequence[str], member_set: set, ctx: str) -> None:
    for name in names:
        if name not in member_set:
            raise ValidationError(f"{ctx}: unknown member {name!r}")


def compute_shares(amount_paise: int, split: Mapping[str, Any],
                   members: Sequence[str]) -> Dict[str, int]:
    """Turn a split spec into {member: paise} summing exactly to amount_paise."""
    if amount_paise <= 0:
        raise ValidationError("expense amount must be positive")
    if not isinstance(split, Mapping):
        raise ValidationError("split must be an object with a 'type'")
    stype = split.get("type")
    member_set = set(members)

    if stype == "equal":
        participants = list(split.get("members", members))
        if not participants:
            raise ValidationError("equal split needs at least one participant")
        _validate_members(participants, member_set, "equal split")
        if len(set(participants)) != len(participants):
            raise ValidationError("equal split lists a member twice")
        base, rem = divmod(amount_paise, len(participants))
        shares = {m: base for m in participants}
        for i in range(rem):  # distribute the leftover paise one by one
            shares[participants[i]] += 1
        return shares

    if stype == "exact":
        raw = split.get("amounts")
        if not isinstance(raw, Mapping) or not raw:
            raise ValidationError("exact split needs a non-empty 'amounts' object")
        _validate_members(list(raw), member_set, "exact split")
        shares = {m: to_paise(v) for m, v in raw.items()}
        if sum(shares.values()) != amount_paise:
            raise ValidationError(
                f"exact amounts sum to {format_money(sum(shares.values()))}, "
                f"but the expense total is {format_money(amount_paise)}")
        return shares

    if stype == "percentage":
        raw = split.get("percentages")
        if not isinstance(raw, Mapping) or not raw:
            raise ValidationError("percentage split needs a non-empty 'percentages' object")
        _validate_members(list(raw), member_set, "percentage split")
        pcts = [(m, _to_percent(v)) for m, v in raw.items()]
        if sum(p for _, p in pcts) != 10000:  # 100.00 * 100
            raise ValidationError(
                f"percentages sum to {sum(p for _, p in pcts) / 100}, expected 100")
        shares: Dict[str, int] = {}
        remaining = amount_paise
        for i, (m, p) in enumerate(pcts):
            if i == len(pcts) - 1:
                shares[m] = remaining  # last member absorbs rounding
            else:
                shares[m] = amount_paise * p // 10000  # floor keeps the sum exact
                remaining -= shares[m]
        return shares

    raise ValidationError(f"unknown split type {stype!r} (use equal/exact/percentage)")


# --------------------------------------------------------------------------- #
# Splitter
# --------------------------------------------------------------------------- #

class Splitter:
    """Tracks a group's expenses, net balances and minimal settlements."""

    def __init__(self, members: Sequence[str]):
        if not members:
            raise ValidationError("group must have at least one member")
        if len(set(members)) != len(members):
            raise ValidationError("member names must be unique")
        self.members: Tuple[str, ...] = tuple(members)
        self.expenses: List[Tuple[str, str, int, Dict[str, int]]] = []
        self._balance: Dict[str, int] = {m: 0 for m in self.members}

    def add_expense(self, payer: str, amount: Any, split: Mapping[str, Any],
                    description: str = "") -> "Splitter":
        if payer not in self._balance:
            raise ValidationError(f"payer {payer!r} is not a group member")
        paise = to_paise(amount)
        shares = compute_shares(paise, split, self.members)
        self._balance[payer] += paise
        for member, share in shares.items():
            self._balance[member] -= share
        self.expenses.append((payer, description, paise, shares))
        return self  # allow chaining

    def balances(self) -> Dict[str, int]:
        """Net balance per member in paise (positive = owed money)."""
        return dict(self._balance)

    def settlements(self) -> List[Tuple[str, str, int]]:
        """Greedy debt simplification: a near-minimal list of (payer, payee, paise).

        Always at most len(members) - 1 settlements; each clears the largest
        debtor against the largest creditor, which is optimal for most cases.
        """
        bal = dict(self._balance)
        debtors = sorted((m for m in self.members if bal[m] < 0), key=lambda m: bal[m])
        creditors = sorted((m for m in self.members if bal[m] > 0),
                           key=lambda m: bal[m], reverse=True)
        out: List[Tuple[str, str, int]] = []
        i = j = 0
        while i < len(debtors) and j < len(creditors):
            d, c = debtors[i], creditors[j]
            amt = min(-bal[d], bal[c])
            if amt > 0:
                out.append((d, c, amt))
            bal[d] += amt
            bal[c] -= amt
            if bal[d] == 0:
                i += 1
            if bal[c] == 0:
                j += 1
        return out


# --------------------------------------------------------------------------- #
# JSON processing & CLI
# --------------------------------------------------------------------------- #

def process(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate a JSON payload and return a summary (balances + settlements)."""
    if not isinstance(payload, Mapping):
        raise ValidationError("top-level JSON must be an object")
    members = payload.get("members")
    if (not isinstance(members, list) or not members
            or not all(isinstance(m, str) for m in members)):
        raise ValidationError("'members' must be a non-empty list of strings")
    s = Splitter(members)
    raw = payload.get("expenses", [])
    if isinstance(raw, Mapping):  # M4: a single expense object is accepted
        raw = [raw]
    if not isinstance(raw, list):
        raise ValidationError("'expenses' must be a list of expense objects")
    for i, e in enumerate(raw):
        if not isinstance(e, Mapping):
            raise ValidationError(f"expense #{i + 1} must be an object")
        try:
            s.add_expense(e.get("payer"), e.get("amount"), e.get("split"),
                          description=str(e.get("description", "")))
        except ValidationError as exc:
            raise ValidationError(f"expense #{i + 1}: {exc}") from exc
    return summarize(s)


def summarize(s: Splitter) -> Dict[str, Any]:
    balances = s.balances()
    settlements = s.settlements()
    return {
        "members": list(s.members),
        "total_expenses": format_money(sum(e[2] for e in s.expenses)),
        "balances": {m: format_money(v) for m, v in balances.items()},
        "settlements": [{"from": a, "to": b, "amount": format_money(p)}
                        for a, b, p in settlements],
    }


def render(summary: Mapping[str, Any]) -> str:
    lines = ["Balances:"]
    for m, b in summary["balances"].items():
        lines.append(f"  {m}: {b}")
    lines.append("Settlements:")
    if not summary["settlements"]:
        lines.append("  (none — everyone is settled)")
    for s in summary["settlements"]:
        lines.append(f"  {s['from']} pays {s['to']} {s['amount']}")
    return "\n".join(lines)


def load_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print("usage: python expense_splitter.py <expenses.json> [...]  ('-' reads stdin)\n"
              "       python expense_splitter.py --json <expenses.json>", file=sys.stderr)
        return 2
    as_json = argv[1] == "--json"
    paths = argv[2:] if as_json else argv[1:]
    for path in paths:
        try:
            summary = process(load_json(path))
            print(json.dumps(summary, ensure_ascii=False, indent=2) if as_json
                  else render(summary))
        except (ValidationError, json.JSONDecodeError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
