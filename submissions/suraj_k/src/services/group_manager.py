"""
GroupManager — the aggregate root that owns members and expenses.

This is the primary entry point for building up a group programmatically.
It enforces all business rules at the boundary and supports soft-delete
of members (preserving historical referential integrity).
"""

from __future__ import annotations

from decimal import Decimal

from src.errors import InactiveMemberError, MemberNotFoundError
from src.models.expense import Expense
from src.models.member import Member
from src.models.split import split_from_dict
from src.models.transaction import BalanceSnapshot, Transaction
from src.services.balance import BalanceCalculator
from src.services.settlement import SettlementEngine


class GroupManager:
    """Manages a group of members and their shared expenses."""

    def __init__(self, name: str = "") -> None:
        self.name: str = name
        self._members: dict[str, Member] = {}       # name → Member (all, including inactive)
        self._members_by_id: dict[str, Member] = {} # id → Member
        self._expenses: list[Expense] = []

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------

    @property
    def members(self) -> list[Member]:
        """All members (including inactive)."""
        return list(self._members.values())

    @property
    def active_members(self) -> list[Member]:
        """Only active members."""
        return [m for m in self._members.values() if m.is_active]

    @property
    def member_count(self) -> int:
        """Count of all members (including inactive)."""
        return len(self._members)

    @property
    def active_member_count(self) -> int:
        """Count of active members only."""
        return len(self.active_members)

    @property
    def expense_count(self) -> int:
        return len(self._expenses)

    @property
    def expenses(self) -> list[Expense]:
        return list(self._expenses)

    @property
    def total_spent(self) -> Decimal:
        return sum((e.total_amount for e in self._expenses), Decimal("0"))

    def add_member(self, name: str) -> Member:
        if name in self._members:
            raise MemberNotFoundError(f"Member '{name}' already exists")
        m = Member(name)
        self._members[name] = m
        self._members_by_id[m.id] = m
        return m

    def deactivate_member(self, name: str) -> None:
        """Soft-delete a member.

        The member remains in _members and all historical expenses still
        reference it.  Future splits may not include this member.
        Net balances and settlements will still show this member's
        obligations.
        """
        m = self._members.get(name)
        if m is None:
            raise MemberNotFoundError(f"Member '{name}' is not in the group")
        if not m.is_active:
            raise InactiveMemberError(f"Member '{name}' is already deactivated")
        m.deactivate()

    def reactivate_member(self, name: str) -> None:
        """Re-activate a previously deactivated member."""
        m = self._members.get(name)
        if m is None:
            raise MemberNotFoundError(f"Member '{name}' is not in the group")
        if m.is_active:
            raise InactiveMemberError(f"Member '{name}' is already active")
        m.active = True

    def get_member_by_name(self, name: str) -> Member:
        m = self._members.get(name)
        if m is None:
            raise MemberNotFoundError(f"Member '{name}' is not in the group")
        return m

    def get_member_by_id(self, member_id: str) -> Member:
        m = self._members_by_id.get(member_id)
        if m is None:
            raise MemberNotFoundError(f"Member with id '{member_id}' is not in the group")
        return m

    def _member_map(self) -> dict[str, Member]:
        """All members (including inactive) for historical lookups."""
        return dict(self._members)

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def add_expense(
        self,
        description: str,
        payer_name: str,
        amount: Decimal,
        split_data: dict | None = None,
    ) -> Expense:
        """Add an expense with a payer and optional split specification.

        If split_data is None, defaults to an equal split across all
        *active* members.

        Raises MemberNotFoundError if the payer or any participant is
        missing or inactive.
        """
        payer = self._members.get(payer_name)
        if payer is None:
            raise MemberNotFoundError(f"Payer '{payer_name}' is not a member of the group")
        if not payer.is_active:
            raise InactiveMemberError(
                f"Payer '{payer_name}' is deactivated and cannot pay for new expenses"
            )

        if split_data is None:
            # Default: equal split across all active members.
            active_names = [m.name for m in self.active_members]
            if len(active_names) < 1:
                raise MemberNotFoundError("No active members in the group")
            split_data = {
                "type": "equal",
                "participants": active_names,
            }

        split = split_from_dict(
            split_data,
            self._member_map(),
            amount,
            list(self._members.values()),
        )

        expense = Expense(
            description=description,
            payer=payer,
            total_amount=amount,
            split=split,
        )
        self._expenses.append(expense)
        return expense

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def net_balances(self) -> list[BalanceSnapshot]:
        """Compute net balances across all expenses (includes inactive members)."""
        return BalanceCalculator.compute(self._expenses)

    def net_balances_as_dicts(self) -> list[dict]:
        """JSON-serializable balance output."""
        return BalanceCalculator.to_dicts(self.net_balances())

    def simplify_debts(self) -> list[Transaction]:
        """Minimize settlements — includes inactive members who owe or are owed."""
        return SettlementEngine.simplify(self.net_balances())

    def summary(self) -> dict:
        """Full JSON-serializable summary: balances + settlements."""
        balances = self.net_balances()
        settlements = SettlementEngine.simplify(balances)
        return {
            "group": self.name,
            "member_count": self.active_member_count,
            "total_member_count": self.member_count,
            "expense_count": self.expense_count,
            "total_spent": str(self.total_spent),
            "net_balances": BalanceCalculator.to_dicts(balances),
            "settlements": [
                {
                    "from": t.from_member.name,
                    "to": t.to_member.name,
                    "amount": str(t.amount),
                }
                for t in settlements
            ],
        }