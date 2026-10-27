"""Tests for the agent entry point — run() and run_batch()."""

import json
import pytest

from agent import run, run_batch
from models import TriageResult


class TestAgentRun:
    def test_run_with_json_input(self):
        ticket_json = json.dumps({
            "ticket_id": "T-AG-001",
            "subject": "Cannot download invoice",
            "body": "I need my invoice for last month but the download link gives a 404.",
            "sender_email": "billing@company.com",
        })
        result = run(ticket_json)
        assert isinstance(result, TriageResult)
        assert result.ticket_id == "T-AG-001"

    def test_run_with_plain_text(self):
        result = run("My app is crashing when I open the reports page. Please help!")
        assert isinstance(result, TriageResult)
        assert result.ticket_id.startswith("AUTO-")

    def test_run_produces_classification(self):
        result = run("How do I set up two-factor authentication?")
        assert result.classification is not None
        assert result.classification.category is not None

    def test_run_produces_routing(self):
        result = run("I was double-charged on my last invoice. Refund me now.")
        assert result.route_to is not None

    def test_run_logs_actions(self):
        result = run("Password reset link is broken, please fix.")
        assert len(result.actions) > 0


class TestAgentRunBatch:
    def test_run_batch_multiple(self):
        tasks = [
            json.dumps({"ticket_id": "T-B01", "subject": "Bug 1", "body": "App crash on save.", "sender_email": "a@b.com"}),
            json.dumps({"ticket_id": "T-B02", "subject": "Bug 2", "body": "PDF export is blank.", "sender_email": "c@d.com"}),
        ]
        results = run_batch(tasks)
        assert len(results) == 2
        assert results[0].ticket_id == "T-B01"
        assert results[1].ticket_id == "T-B02"

    def test_run_batch_empty(self):
        results = run_batch([])
        assert results == []