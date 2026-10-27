"""
Expense Splitter with Debt Simplification — Core Module
======================================================
A Splitwise-lite tool that handles:
  - Equal, exact, and percentage split expenses
  - Net balance calculation per member
  - Debt simplification (minimum transactions)
  - Input validation for all constraints
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Expense:
    """A single expense entry."""

    title: str
    total_amount: Decimal
    paid_by: str
    split_type: str  # "equal" | "exact" | "percentage"
    shares: Dict[str, Decimal]  # member -> amount owed (exact) or percentage
    members: List[str]  # all members involved in this expense

    def __post_init__(self) -> None:
        if self.split_type not in ("equal", "exact", "percentage"):
            raise ValueError(f"Unknown split_type '{self.split_type}'")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Build an Expense from a raw dictionary (JSON input)."""
        total = _to_decimal(data["total_amount"])
        paid_by: str = data["paid_by"]
        split_type: str = data["split_type"]
        # Deduplicate while preserving order
        raw_members = data.get("members", [])
        members = list(dict.fromkeys(raw_members))

        # Build shares dict
        raw_shares: Dict[str, Any] = data.get("shares", {})

        # Ensure payer is in members
        if paid_by not in members:
            members.append(paid_by)

        # For exact/percentage splits, include all share participants in members
        if split_type in ("exact", "percentage"):
            for m in raw_shares:
                if m not in members:
                    members.append(m)

        shares: Dict[str, Decimal] = {}
        if split_type == "equal":
            # All members split equally (payer included).
            # Use round-robin distribution so 100/3 → [33.34, 33.33, 33.33]
            num = len(members)
            per_person = (total / Decimal(num)).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            remainder = total - per_person * Decimal(num - 1)
            if remainder < 0:
                remainder = Decimal("0")
            shares[members[0]] = remainder
            for m in members[1:]:
                shares[m] = per_person
        elif split_type == "exact":
            for m, v in raw_shares.items():
                shares[m] = _to_decimal(v)
        elif split_type == "percentage":
            # Convert percentages to actual amounts.
            # Handle rounding: distribute any remainder to the first member.
            total_pct = sum(Decimal(str(v)) for v in raw_shares.values())
            if total_pct == Decimal("0"):
                raise ValueError("Total percentage cannot be zero")
            members_with_pct = list(raw_shares.keys())
            for m in members_with_pct:
                pct = Decimal(str(raw_shares[m]))
                shares[m] = (total * pct / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            # Adjust any rounding discrepancy on the first member
            allocated = sum(shares.values())
            diff = total - allocated
            if diff != 0 and members_with_pct:
                shares[members_with_pct[0]] += diff

        return cls(
            title=data.get("title", ""),
            total_amount=total,
            paid_by=paid_by,
            split_type=split_type,
            shares=shares,
            members=members,
        )


def _to_decimal(value: Any) -> Decimal:
    """Safely convert an int/float/str to Decimal with 2-place precision."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when input data fails validation."""


def validate_expense(data: Dict[str, Any], group_members: List[str]) -> None:
    """Validate a single expense dictionary against all rules.

    Raises ValidationError on first violation.
    """
    errors: List[str] = []

    # --- Required fields ---
    if "total_amount" not in data:
        errors.append("Missing 'total_amount'")
    if "paid_by" not in data:
        errors.append("Missing 'paid_by'")
    if "split_type" not in data:
        errors.append("Missing 'split_type'")

    if errors:
        raise ValidationError("; ".join(errors))

    total = data["total_amount"]
    paid_by: str = data["paid_by"]
    split_type: str = data["split_type"]
    members: List[str] = data.get("members", [])
    shares: Dict[str, Any] = data.get("shares", {})

    # --- Split type ---
    if split_type not in ("equal", "exact", "percentage"):
        raise ValidationError(
            f"Invalid split_type '{split_type}'; must be 'equal', 'exact', or 'percentage'"
        )

    # --- total_amount must be positive ---
    try:
        total_d = Decimal(str(total))
    except Exception:
        raise ValidationError(f"Invalid total_amount '{total}'")
    if total_d <= 0:
        raise ValidationError("total_amount must be positive")

    # --- paid_by must be a group member ---
    if paid_by not in group_members:
        raise ValidationError(f"payer '{paid_by}' is not a group member")

    # --- members must belong to the group ---
    for m in members:
        if m not in group_members:
            raise ValidationError(f"member '{m}' is not a group member")

    # Ensure payer in members list for equal split
    if paid_by not in members:
        if split_type == "equal":
            # Equal split always includes payer
            members = [paid_by] + members
        else:
            members = [paid_by] + members

    # --- Split-type specific ---
    if split_type == "exact":
        # Exact split requires a shares dict
        if not shares:
            raise ValidationError("Exact split requires 'shares'")
        total_shares = sum(Decimal(str(v)) for v in shares.values())
        if total_shares != total_d:
            raise ValidationError(
                f"Exact amounts sum to {total_shares}, expected {total_d}"
            )
        for m, v in shares.items():
            if m not in group_members:
                raise ValidationError(f"share member '{m}' is not a group member")
            if Decimal(str(v)) < 0:
                raise ValidationError(f"Negative amount for '{m}'")

    elif split_type == "percentage":
        # Percentage split requires a shares dict summing to exactly 100
        if not shares:
            raise ValidationError("Percentage split requires 'shares'")
        total_pct = sum(Decimal(str(v)) for v in shares.values())
        if total_pct != Decimal("100"):
            raise ValidationError(
                f"Percentages sum to {total_pct}%, expected 100%"
            )
        for m, v in shares.items():
            if m not in group_members:
                raise ValidationError(f"share member '{m}' is not a group member")
        # Each percentage must be >= 0
        for m, v in shares.items():
            if Decimal(str(v)) < 0:
                raise ValidationError(f"Negative percentage for '{m}'")

    # --- Members list must not be empty for equal split ---
    if split_type == "equal" and not members:
        raise ValidationError("No members to split equally")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_net_balances(
    expenses: List[Expense],
) -> Dict[str, Decimal]:
    """Compute each member's net balance.

    Positive  → is owed money (creditor)
    Negative  → owes money (debtor)
    """
    balances: Dict[str, Decimal] = {}

    for exp in expenses:
        # Payer paid this amount → they are owed from others
        payer = exp.paid_by
        balances.setdefault(payer, Decimal("0"))
        balances[payer] += exp.total_amount

        # Each member owes their share
        for member, share in exp.shares.items():
            balances.setdefault(member, Decimal("0"))
            balances[member] -= share

    # Round all to 2 decimals
    for person in balances:
        balances[person] = balances[person].quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return balances


def simplify_debts(
    balances: Dict[str, Decimal],
) -> List[Tuple[str, str, Decimal]]:
    """Reduce debts to a near-minimum set of transactions.

    Uses the greedy "max creditor ↔ max debtor" matching algorithm.
    While not guaranteed optimal (minimum-transaction settlement is NP-hard),
    this approach is provably near-optimal for typical group sizes.

    Returns a list of (debtor, creditor, amount) tuples.
    """
    # Separate creditors (>0) and debtors (<0)
    creditors: List[Tuple[str, Decimal]] = []
    debtors: List[Tuple[str, Decimal]] = []

    for person, bal in balances.items():
        rounded = bal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded > Decimal("0"):
            creditors.append((person, rounded))
        elif rounded < Decimal("0"):
            debtors.append((person, -rounded))  # store positive debt amount

    # Sort descending by amount
    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    settlements: List[Tuple[str, str, Decimal]] = []
    ci, di = 0, 0

    while ci < len(creditors) and di < len(debtors):
        creditor, cred_amt = creditors[ci]
        debtor, debt_amt = debtors[di]

        transfer = min(cred_amt, debt_amt)
        if transfer > Decimal("0.005"):  # ignore sub-paisa rounding dust
            settlements.append((debtor, creditor, transfer))

        # Update remaining amounts
        creditors[ci] = (creditor, cred_amt - transfer)
        debtors[di] = (debtor, debt_amt - transfer)

        if creditors[ci][1] < Decimal("0.005"):
            ci += 1
        if debtors[di][1] < Decimal("0.005"):
            di += 1

    return settlements


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------

def process_group(
    group_name: str,
    members: List[str],
    expenses_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate, compute balances, and simplify debts for a group.

    Returns a structured result dict.
    """
    # Validate every expense
    for ed in expenses_data:
        validate_expense(ed, members)

    # Parse into Expense objects
    expenses = [Expense.from_dict(ed) for ed in expenses_data]

    # Compute net balances
    balances = compute_net_balances(expenses)

    # Simplify debts
    settlements = simplify_debts(balances)

    return {
        "group": group_name,
        "members": members,
        "expenses": [
            {
                "title": e.title,
                "total_amount": float(e.total_amount),
                "paid_by": e.paid_by,
                "split_type": e.split_type,
                "shares": {m: float(v) for m, v in e.shares.items()},
            }
            for e in expenses
        ],
        "balances": {p: float(b) for p, b in balances.items()},
        "settlements": [
            {"from": d, "to": c, "amount": float(a)}
            for d, c, a in settlements
        ],
    }


def process_batch(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process a batch input containing one or more groups.

    Expected format:
      {
        "groups": [
          {
            "name": "...",
            "members": ["A", "B", ...],
            "expenses": [ {...}, ... ]
          },
          ...
        ]
      }
    """
    groups = data.get("groups", [data])  # support single-group shorthand
    results = []
    for g in groups:
        result = process_group(
            group_name=g.get("name", g.get("group", "Unnamed")),
            members=g["members"],
            expenses_data=g["expenses"],
        )
        results.append(result)

    return {"results": results}