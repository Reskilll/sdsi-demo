"""Tests for the ActionLogger — verify logging behaviour."""

import os
import tempfile
from pathlib import Path

import pytest

from logger import ActionLogger
from models import ActionLog, ActionType


class TestActionLogger:
    def test_logs_and_retrieves(self) -> None:
        logger = ActionLogger()
        logger.log(ActionLog(
            ticket_id="T-001",
            action=ActionType.CLASSIFY,
            detail={"message": "first"},
        ))
        logger.log(ActionLog(
            ticket_id="T-001",
            action=ActionType.ROUTE,
            detail={"message": "second"},
        ))
        logger.log(ActionLog(
            ticket_id="T-002",
            action=ActionType.DRAFT,
            detail={"message": "third"},
        ))

        assert len(logger.all()) == 3
        assert len(logger.by_ticket("T-001")) == 2
        assert len(logger.by_ticket("T-002")) == 1
        assert len(logger.by_ticket("T-999")) == 0

    def test_writes_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "test.log"
            logger = ActionLogger(log_path=log_path)
            logger.log(ActionLog(
                ticket_id="T-001",
                action=ActionType.CLASSIFY,
                detail={"message": "hello file"},
            ))
            # File should exist and contain the message
            assert log_path.exists()
            content = log_path.read_text(encoding="utf-8")
            assert "hello file" in content
            assert "T-001" in content
            assert "classify" in content

    def test_empty_logger(self) -> None:
        logger = ActionLogger()
        assert logger.all() == []
        assert logger.by_ticket("any") == []