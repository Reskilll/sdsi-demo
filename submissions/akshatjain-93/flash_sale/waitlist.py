"""Waitlist mechanism for out-of-stock flash sale products (Stretch Feature)."""

import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, Deque, Optional, List, Any


@dataclass
class WaitlistEntry:
    entry_id: str
    user_id: str
    sku: str
    requested_qty: int
    joined_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WaitlistManager:
    """
    Manages per-SKU FIFO waitlists for users who attempted to purchase
    when stock was depleted.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._waitlists: Dict[str, Deque[WaitlistEntry]] = {}

    def join(self, entry_id: str, user_id: str, sku: str, requested_qty: int) -> int:
        """
        Adds user to waitlist for a SKU. Returns their 1-based position in queue.
        """
        with self._lock:
            if sku not in self._waitlists:
                self._waitlists[sku] = deque()
            
            # Check if user already in waitlist for this SKU
            for idx, item in enumerate(self._waitlists[sku]):
                if item.user_id == user_id:
                    return idx + 1

            entry = WaitlistEntry(
                entry_id=entry_id,
                user_id=user_id,
                sku=sku,
                requested_qty=requested_qty,
                joined_at=time.time(),
            )
            self._waitlists[sku].append(entry)
            return len(self._waitlists[sku])

    def pop_next_eligible(self, sku: str, available_stock: int) -> Optional[WaitlistEntry]:
        """
        Pops the next entry that can be satisfied with the available stock.
        """
        with self._lock:
            if sku not in self._waitlists or not self._waitlists[sku]:
                return None

            queue = self._waitlists[sku]
            for i in range(len(queue)):
                entry = queue[i]
                if entry.requested_qty <= available_stock:
                    del queue[i]
                    return entry
            return None

    def get_queue(self, sku: str) -> List[WaitlistEntry]:
        """Returns list of waitlist entries for a SKU."""
        with self._lock:
            return list(self._waitlists.get(sku, []))

    def get_position(self, user_id: str, sku: str) -> Optional[int]:
        """Returns 1-based position of user in queue, or None if not found."""
        with self._lock:
            if sku not in self._waitlists:
                return None
            for idx, entry in enumerate(self._waitlists[sku]):
                if entry.user_id == user_id:
                    return idx + 1
            return None

    def remove(self, user_id: str, sku: str) -> bool:
        """Removes a user from the waitlist."""
        with self._lock:
            if sku not in self._waitlists:
                return False
            original_len = len(self._waitlists[sku])
            self._waitlists[sku] = deque(
                e for e in self._waitlists[sku] if e.user_id != user_id
            )
            return len(self._waitlists[sku]) < original_len

