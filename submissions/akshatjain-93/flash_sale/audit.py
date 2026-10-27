"""Audit logging ledger for flash sale events and state transitions."""

import threading
import time
import uuid
from typing import List, Optional, Dict, Any
from .models import AuditEvent


class AuditLedger:
    """
    Thread-safe ledger recording immutable events for every reservation,
    confirmation, cancellation, expiration, and waitlist action.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._events: List[AuditEvent] = []

    def record(
        self,
        event_type: str,
        sku: Optional[str] = None,
        user_id: Optional[str] = None,
        quantity: Optional[int] = None,
        reservation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Records an audit event in the ledger."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=time.time(),
            sku=sku,
            user_id=user_id,
            quantity=quantity,
            reservation_id=reservation_id,
            details=details or {},
        )
        with self._lock:
            self._events.append(event)
        return event

    def get_events(
        self,
        event_type: Optional[str] = None,
        sku: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[AuditEvent]:
        """Returns filtered list of events."""
        with self._lock:
            events = list(self._events)

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if sku:
            events = [e for e in events if e.sku == sku]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        return events

    def get_count(self) -> int:
        """Returns total number of events recorded."""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Clears all audit events."""
        with self._lock:
            self._events.clear()
