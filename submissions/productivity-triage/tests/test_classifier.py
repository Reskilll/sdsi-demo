"""Tests for the Classifier — uses the LLM via LangChain.

These tests make LIVE API calls to the configured LLM.
Set OPENAI_API_KEY in the environment before running.
Skip them with:  pytest -m "not integration"
"""

import pytest

from classifier import Classifier
from models import Ticket


@pytest.fixture
def classifier() -> Classifier:
    return Classifier()


@pytest.mark.integration
class TestClassifierIntegration:

    BUG_TICKET = Ticket(
        ticket_id="T-BUG-001",
        subject="App crashes when I click Save",
        body=(
            "Every time I click the Save button on the settings page the app "
            "crashes to desktop. I've tried on Windows 11 and macOS. This "
            "started after the v2.4 update. I've lost work twice."
        ),
        sender_email="dev@example.com",
    )

    FEATURE_TICKET = Ticket(
        ticket_id="T-FEAT-001",
        subject="Please add dark mode",
        body="I'd really like a dark mode option. Every other app has one now.",
        sender_email="user@example.com",
    )

    BILLING_TICKET = Ticket(
        ticket_id="T-BILL-001",
        subject="Overcharged on last invoice",
        body=(
            "My invoice #INV-9823 shows $499 but my plan is $299. "
            "Please refund the difference immediately."
        ),
        sender_email="customer@example.com",
    )

    SPAM_TICKET = Ticket(
        ticket_id="T-SPAM-001",
        subject="BUY CHEAP VIAGRA NOW!!!",
        body="Click here for amazing deals!!! http://spam.example.com",
        sender_email="spammer@bad.com",
    )

    OUTAGE_TICKET = Ticket(
        ticket_id="T-OUT-001",
        subject="API completely down — all requests failing",
        body=(
            "Our production system cannot reach the API. All requests return "
            "502 Bad Gateway. This started 15 minutes ago and is affecting "
            "all our customers. URGENT."
        ),
        sender_email="ops@customer.com",
    )

    def test_classify_bug(self, classifier: Classifier):
        result = classifier.classify(self.BUG_TICKET)
        assert result.category.value in ("bug", "unknown")
        assert 0.0 <= result.confidence <= 1.0
        assert result.reasoning

    def test_classify_feature_request(self, classifier: Classifier):
        result = classifier.classify(self.FEATURE_TICKET)
        assert result.category.value in ("feature_request", "unknown")
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_billing(self, classifier: Classifier):
        result = classifier.classify(self.BILLING_TICKET)
        assert result.category.value in ("billing", "unknown")
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_spam(self, classifier: Classifier):
        result = classifier.classify(self.SPAM_TICKET)
        assert result.category.value in ("spam", "unknown")

    def test_classify_outage(self, classifier: Classifier):
        result = classifier.classify(self.OUTAGE_TICKET)
        assert result.category.value in ("service_outage", "bug", "unknown")
        # Outage should usually be P0
        if result.category.value == "service_outage":
            assert result.priority.value == "p0"

    def test_classify_returns_priority(self, classifier: Classifier):
        result = classifier.classify(self.BUG_TICKET)
        assert result.priority.value in ("p0", "p1", "p2", "p3", "p4")

    def test_confidence_below_threshold_triggers_escalation(self, classifier: Classifier):
        """Even if confidence is too low, result is still returned.
        The pipeline decides to escalate based on threshold."""
        result = classifier.classify(self.BUG_TICKET)
        # Just ensure we get a valid result regardless of confidence
        assert result.category is not None
        assert isinstance(result.confidence, float)


class TestClassifierUnit:
    """Unit tests that don't call the LLM."""

    def test_parse_valid_json(self):
        from classifier import Classifier
        raw = '{"category":"bug","priority":"p1","confidence":0.92,"reasoning":"Crash report."}'
        result = Classifier._parse(raw, "T-001")
        assert result.category.value == "bug"
        assert result.priority.value == "p1"
        assert result.confidence == 0.92
        assert "Crash" in result.reasoning

    def test_parse_with_markdown_fence(self):
        from classifier import Classifier
        raw = '```json\n{"category":"question","priority":"p3","confidence":0.80,"reasoning":"How-to."}\n```'
        result = Classifier._parse(raw, "T-002")
        assert result.category.value == "question"
        assert result.confidence == 0.80

    def test_parse_invalid_json_fallback(self):
        from classifier import Classifier
        raw = "I'm sorry, I cannot classify this."
        result = Classifier._parse(raw, "T-003")
        assert result.category.value == "unknown"
        assert result.confidence == 0.0
        assert "Failed to parse" in result.reasoning