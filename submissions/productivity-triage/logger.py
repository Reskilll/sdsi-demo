"""Action logger — logs every action to a structured log file."""

from __future__ import annotations

import logging
from pathlib import Path

from config import LOG_FILE, LOG_FORMAT
from models import ActionLog


class ActionLogger:
    """Structured logger that records every agent action with a ticket context."""

    def __init__(self, log_path: Path | None = None) -> None:
        path = log_path or LOG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[ActionLog] = []

        self._logger = logging.getLogger("triage")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()  # idempotent across re-creations

        handler = logging.FileHandler(str(path), encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        self._logger.addHandler(handler)
        self._logger.propagate = False

    # -- public API -----------------------------------------------------------

    def log(self, record: ActionLog) -> None:
        """Persist and store a single action record."""
        self._records.append(record)
        self._logger.info(
            record.detail.get("message", ""),
            extra={
                "action": record.action.value,
                "ticket_id": record.ticket_id,
            },
        )

    def all(self) -> list[ActionLog]:
        """Return every logged action for this session (in-memory)."""
        return list(self._records)

    def by_ticket(self, ticket_id: str) -> list[ActionLog]:
        """Filter logged actions by ticket id."""
        return [r for r in self._records if r.ticket_id == ticket_id]