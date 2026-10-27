"""Tests for models — verify data validation and defaults."""

import pytest
from datetime import datetime

from models import (
    Ticket,
    TicketCategory,
    TicketPriority,
    ActionType,
    ClassificationResult,
    TriageResult,
    DraftResponse,
    RetrievedDocument,
    ActionLog,
)


class TestTicket:
    def test_valid_ticket(self):
        t = Ticket(
            ticket_id="T-001",
            subject="Cannot log in",
            body="I've been trying for an hour. Password reset doesn't work.",
            sender_email="user@example.com",
        )
        assert t.ticket_id == "T-001"
        assert isinstance(t.received_at, datetime)

    def test_ticket_defaults(self):
        t = Ticket(ticket_id="T-002", subject="Help", body="Need help with billing")
        assert t.sender_email is None

    def test_ticket_empty_subject_raises(self):
        with pytest.raises(Exception):
            Ticket(ticket_id="T-003", subject="", body="some body")

    def test_ticket_empty_body_raises(self):
        with pytest.raises(Exception):
            Ticket(ticket_id="T-003", subject="Hi", body="")


class TestClassificationResult:
    def test_valid(self):
        r = ClassificationResult(
            category=TicketCategory.bug,
            confidence=0.95,
            priority=TicketPriority.p1,
            reasoning="User reports a reproducible crash on login.",
        )
        assert r.category == TicketCategory.bug
        assert r.confidence == 0.95

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ClassificationResult(
                category=TicketCategory.question,
                confidence=1.5,
                priority=TicketPriority.p3,
                reasoning="oops",
            )

    def test_unknown_category(self):
        r = ClassificationResult(
            category=TicketCategory.unknown,
            confidence=0.1,
            priority=TicketPriority.p3,
            reasoning="Could not classify.",
        )
        assert r.category == TicketCategory.unknown


class TestTriageResult:
    def test_minimal(self):
        cl = ClassificationResult(
            category=TicketCategory.question,
            confidence=0.9,
            priority=TicketPriority.p3,
            reasoning="It's a how-to question.",
        )
        r = TriageResult(ticket_id="T-001", classification=cl)
        assert r.ticket_id == "T-001"
        assert r.escalated is False
        assert r.draft is None
        assert r.retrieved_docs == []

    def test_escalated_p0(self):
        cl = ClassificationResult(
            category=TicketCategory.service_outage,
            confidence=0.99,
            priority=TicketPriority.p0,
            reasoning="Service is down.",
        )
        r = TriageResult(
            ticket_id="T-005",
            classification=cl,
            escalated=True,
            escalation_reason="P0 — immediate escalation",
        )
        assert r.escalated is True


class TestDraftResponse:
    def test_full_draft(self):
        d = DraftResponse(
            to="user@example.com",
            subject="Re: Refund inquiry",
            body="Thank you for reaching out...",
            policies_referenced=["POLICY: Refund requests... full refund."],
        )
        assert "Refund" in d.subject
        assert len(d.policies_referenced) == 1

    def test_spam_draft(self):
        d = DraftResponse(
            to="spammer@bad.com",
            subject="Re: Buy now!!!",
            body="[SPAM — no response sent]",
        )
        assert d.body.startswith("[SPAM")


class TestRetrievedDocument:
    def test_retrieved_doc(self):
        d = RetrievedDocument(
            content="POLICY: Refund requests under 30 days...",
            source="sample_policies.txt",
            relevance_score=0.87,
        )
        assert d.relevance_score == 0.87
        assert "Refund" in d.content


class TestActionLog:
    def test_log_entry(self):
        l = ActionLog(
            ticket_id="T-001",
            action=ActionType.CLASSIFY,
            detail={"message": "classified as bug"},
        )
        assert isinstance(l.timestamp, datetime)
        assert l.action == ActionType.CLASSIFY

    def test_log_serialisable(self):
        l = ActionLog(
            ticket_id="T-001",
            action=ActionType.ROUTE,
            detail={"message": "routed to engineering-team"},
        )
        d = l.model_dump()
        assert d["ticket_id"] == "T-001"
        assert isinstance(d["timestamp"], str)  # ISO serialised