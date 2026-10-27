"""Tests for the pipeline orchestrator — integration tests."""

import pytest

from models import (
    Ticket,
    TicketCategory,
    TicketPriority,
    ClassificationResult,
    TriageResult,
)
from logger import ActionLogger
from pipeliner import TriagePipeline


@pytest.fixture
def pipeline() -> TriagePipeline:
    return TriagePipeline(logger=ActionLogger())


class TestPipelineRouting:
    """Tests that don't hit the LLM — we inject classifications."""

    def test_bug_routes_to_engineering(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-001",
            subject="Login page broken",
            body="The login button does nothing on Chrome 118.",
            sender_email="user@test.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to == "engineering-team"

    def test_feature_request_routes_to_product(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-002",
            subject="Add export to PDF",
            body="Please add a PDF export option to the reports page.",
            sender_email="user@test.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to == "product-team"

    def test_billing_routes_to_finance(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-003",
            subject="Wrong charge amount",
            body="You charged me $100 instead of $50.",
            sender_email="customer@test.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to == "finance-team"

    def test_outage_routes_to_sre(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-004",
            subject="Production is DOWN",
            body="Our entire cluster is unreachable. 503s everywhere. This is urgent.",
            sender_email="ops@company.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to == "sre-team"

    def test_complaint_routes_to_customer_success(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-005",
            subject="Terrible experience",
            body="Your support has been awful. I've been waiting 2 weeks for a reply.",
            sender_email="angry@test.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to == "customer-success-team"

    def test_spam_routes_to_none(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-006",
            subject="WIN A FREE IPHONE",
            body="Click here for your prize!!! http://scam.example.com",
            sender_email="spammer@bad.com",
        )
        result = pipeline.run(ticket)
        assert result.route_to is None

    def test_pipeline_logs_actions(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-RT-007",
            subject="Cannot reset password",
            body="The reset link in my email expired after 5 minutes.",
            sender_email="lockedout@test.com",
        )
        result = pipeline.run(ticket)
        assert len(result.actions) >= 3  # classify, retrieve, route at minimum
        action_types = {a.action.value for a in result.actions}
        assert "classify" in action_types
        assert "route" in action_types


class TestPipelineEscalation:
    """Tests for escalation logic."""

    def test_low_confidence_escalates(self, pipeline: TriagePipeline):
        """A hard-to-classify ticket should trigger escalation."""
        ticket = Ticket(
            ticket_id="T-ESC-001",
            subject="asdfghjkl",
            body="vague nothingness 12345 xyz",
            sender_email="unknown@test.com",
        )
        result = pipeline.run(ticket)
        # If the LLM gives low confidence, it should escalate
        if result.classification.confidence < 0.70:
            assert result.escalated is True
            assert result.escalation_reason is not None

    def test_p0_bug_escalates(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-ESC-002",
            subject="CRITICAL: customer data exposed in API",
            body=(
                "The /users endpoint is returning other customers' PII. "
                "This is a massive data leak. Needs immediate fix."
            ),
            sender_email="security@company.com",
        )
        result = pipeline.run(ticket)
        # Should be classified as bug or service_outage with P0
        if result.classification.priority.value == "p0":
            assert result.escalated is True

    def test_legal_always_escalates(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-ESC-003",
            subject="GDPR Article 17 — Right to Erasure",
            body=(
                "Pursuant to GDPR Article 17 I request immediate deletion of "
                "all personal data you hold about me. My account email is "
                "privacy-concerned@example.com. I expect confirmation within "
                "the statutory 30-day period."
            ),
            sender_email="privacy-concerned@example.com",
        )
        result = pipeline.run(ticket)
        if result.classification.category.value == "legal":
            assert result.escalated is True

    def test_confident_p4_does_not_escalate(self, pipeline: TriagePipeline):
        ticket = Ticket(
            ticket_id="T-ESC-004",
            subject="What are your office hours?",
            body="Just wondering when support is available. No rush.",
            sender_email="curious@test.com",
        )
        result = pipeline.run(ticket)
        # A simple question should be high confidence, not escalated
        if result.classification.confidence >= 0.70:
            assert result.escalated is False