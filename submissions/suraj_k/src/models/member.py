"""
Member value object — identity by id (UUID), display by name, lifecycle by active flag.

Inactive members preserve referential integrity: historical expenses still
reference them, but they are excluded from new splits and member listings.
"""

from __future__ import annotations

import uuid


class Member:
    """A participant in the group.

    Identity is by `id` (UUID), not `name`, so renames are safe.
    Equality and hashing are wired to the id only.
    """

    __slots__ = ("id", "name", "active")

    def __init__(self, name: str) -> None:
        self.id: str = uuid.uuid4().hex
        self.name: str = name
        self.active: bool = True

    def deactivate(self) -> None:
        """Soft-delete this member.

        Historical expenses still reference this member by id.
        Net balances and settlements will still include this member —
        financial obligations do not vanish on deactivation.

        New expenses may not reference a deactivated member in their
        split participants.
        """
        self.active = False

    @property
    def is_active(self) -> bool:
        return self.active

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Member):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        status = "active" if self.active else "inactive"
        return f"Member(id={self.id[:8]}…, name={self.name!r}, {status})"