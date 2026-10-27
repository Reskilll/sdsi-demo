"""Tests for the drafter — produces first-response drafts."""

import pytest

from models import (
    Ticket,
    TicketCategory,
    TicketPriority,
    ClassificationResult,
    DraftResponse,
)


@pytest.fixture
def bug_ticket() -> Ticket:
    return Ticket(
        ticket_id="T-BUG-002",
        subject="Data export fails with error 500",
        body="When I try to export my data to CSV I get a 500 error. This is blocking our quarterly audit.",
        sender_email="analyst@company.com",
    )


@pytest.fixture
def bug_classification() -> ClassificationResult:
    return ClassificationResult(
        category=TicketCategory.bug,
        confidence=0.92,
        priority=TicketPriority.p1,
        reasoning="500 error on data export — reproducible bug.",
    )


@pytest.fixture
def spam_classification() -> ClassificationResult:
    return ClassificationResult(
        category=TicketCategory.spam,
        confidence=0.98,
        priority=TicketPriority.p4,
        reasoning="Unsolicited promotional content.",
    )


@pytest.fixture
def legal_classification() -> ClassificationResult:
    return ClassificationResult(
        category=TicketCategory.legal,
        confidence=0.95,
        priority=TicketPriority.p1,
        reasoning="GDPR data subject access request.",
    )


class TestDrafterSpam:
    def test_spam_draft_short_circuits(self):
        """Spam tickets get an immediate short-circuit — no LLM call."""
        from drafter import Drafter

        ticket = Ticket(
            ticket_id="T-SPAM-001",
            subject="Cheap watches",
            body="Buy now!",
            sender_email="spam@bad.com",
        )
        drafter = Drafter()
        draft = drafter.draft(ticket, spam_classification)
        assert isinstance(draft, DraftResponse)
        assert "[SPAM" in draft.body.upper()


class TestDrafterLegal:
    def test_legal_draft_withheld(self):
        """Legal tickets get a human-review placeholder."""
        from drafter import Drafter

        ticket = Ticket(
            ticket_id="T-LEGAL-001",
            subject="GDPR deletion request",
            body="I want all my data deleted per GDPR Article 17.",
            sender_email="privacy@example.com",
        )
        drafter = Drafter()
        draft = drafter.draft(ticket, legal_classification)
        assert isinstance(draft, DraftResponse)
        assert "LEGAL" in draft.body.upper()
        assert "human review" in draft.body.lower()


@pytest.mark.integration
class TestDrafterIntegration:
    """Integration tests that hit the LLM and optionally the KB."""

    def test_draft_for_bug_returns_polite_response(self, bug_ticket, bug_classification):
        """A real bug ticket should get a real-ish draft."""
        from drafter import Drafter

        drafter = Drafter()
        try:
            drafter.build_kb()  # may fail if offline; draft still works
        except Exception:
            pass

        draft = drafter.draft(bug_ticket, bug_classification)
        assert isinstance(draft, DraftResponse)
        assert draft.to == "analyst@company.com"
        # Should reference the subject
        assert "Re:" in draft.subject
        # Body should be non-trivial
        assert len(draft.body) > 20

    def test_draft_without_kb_still_works(self, bug_ticket, bug_classification):
        """Drafter should still produce output even if KB is unavailable."""
        from drafter import Drafter
        from rag import KnowledgeBase
        import tempfile
        from pathlib import Path

        # Use a KB with empty directory — will fail to build
        with tempfile.TemporaryDirectory() as tmp:
            kb_dir = Path(tmp) / "empty_kb"
            kb_dir.mkdir()
            # Put one file so DirectoryLoader doesn't crash, but with no useful content
            (kb_dir / "empty.txt").write_text("no useful policy here")

            drafter = Drafter(kb=KnowledgeBase(kb_dir=kb_dir))
            try:
                drafter.build_kb()
            except RuntimeError:
                pass  # expected if empty loader

            draft = drafter.draft(bug_ticket, bug_classification)
            assert isinstance(draft, DraftResponse)
            assert len(draft.body) > 0