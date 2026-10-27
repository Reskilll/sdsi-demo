"""
In-memory group store for the web application.

Maps group_id → GroupManager so that multiple groups can coexist
in the same server session.  Not persisted across restarts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.errors import MemberNotFoundError
from src.services.group_manager import GroupManager


@dataclass
class GroupStore:
    """Thread-safe-ish dict of active groups.

    For a hackathon-grade server this is sufficient.  Production
    would use Redis or a database.
    """

    _groups: dict[str, GroupManager] = field(default_factory=dict)

    def create(self, name: str) -> str:
        """Create a new group, return its id."""
        gid = uuid.uuid4().hex[:12]
        self._groups[gid] = GroupManager(name)
        return gid

    def get(self, group_id: str) -> GroupManager:
        if group_id not in self._groups:
            raise MemberNotFoundError(f"Group '{group_id}' not found")
        return self._groups[group_id]

    def delete(self, group_id: str) -> None:
        self._groups.pop(group_id, None)


# Singleton shared by all requests.
store = GroupStore()