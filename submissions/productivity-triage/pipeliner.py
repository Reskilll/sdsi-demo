"""Pipeline — wires classification → retrieval → routing → draft → escalate."""

from __future__ import annotations

from classifier import Classifier
from config import CATEGORY_ROUTING, CONFIDENCE_THRESHOLD
from drafter import Drafter
from logger import ActionLogger
from models import (
    ActionLog,
    ActionType,
    DraftResponse,
    Ticket,
    TicketCategory,
    TriageResult,
)
from rag import KnowledgeBase
from retriever import retrieve_context


class TriagePipeline:
    """Orchestrates the full triage flow for a single ticket.

    Flow:
    1. Classify — LLM assigns category + priority + confidence
    2. Retrieve — pull relevant policies from the KB
    3. Route   — map category to a team
    4. Draft   — generate first-response (LLM + RAG)
    5. Escalate — human review if confidence < threshold or category is legal
    """

    def __init__(
        self,
        logger: ActionLogger | None = None,
        classifier: Classifier | None = None,
        drafter: Drafter | None = None,
        kb: KnowledgeBase | None = None,
    ) -> None:
        self.logger = logger or ActionLogger()
        self._classifier = classifier or Classifier()
        self._kb = kb or KnowledgeBase()
        self._drafter = drafter or Drafter(kb=self._kb)

    # -- run ------------------------------------------------------------------

    def run(self, ticket: Ticket) -> TriageResult:
        """Execute the full pipeline against *ticket* and return the result."""

        # 1. Classify
        classification = self._classifier.classify(ticket)
        self._log(ticket.ticket_id, ActionType.CLASSIFY, f"category={classification.category.value} confidence={classification.confidence:.2f} priority={classification.priority.value}")

        # 2. Retrieve relevant policies
        self._ensure_kb()
        query = f"{ticket.subject}\n{ticket.body}"
        docs = retrieve_context(self._kb, query)
        self._log(ticket.ticket_id, ActionType.RETRIEVE, f"retrieved {len(docs)} docs")

        # 3. Route
        route_to = CATEGORY_ROUTING.get(classification.category.value)
        self._log(ticket.ticket_id, ActionType.ROUTE, f"routed to {route_to or 'none'}")

        # 4. Draft
        draft: DraftResponse | None = None
        escalate = False
        escalation_reason: str | None = None

        if classification.category == TicketCategory.spam:
            self._log(ticket.ticket_id, ActionType.DISCARD, "spam detected, no draft")
            draft = DraftResponse(
                to=ticket.sender_email or "",
                subject=f"Re: {ticket.subject}",
                body="[SPAM — discarded]",
            )

        else:
            draft = self._drafter.draft(ticket, classification)
            self._log(ticket.ticket_id, ActionType.DRAFT, "draft generated")

        # 5. Escalate?
        if classification.confidence < CONFIDENCE_THRESHOLD:
            escalate = True
            escalation_reason = (
                f"Low confidence: {classification.confidence:.2f} < {CONFIDENCE_THRESHOLD:.2f}"
            )
            self._log(ticket.ticket_id, ActionType.ESCALATE, escalation_reason)

        elif classification.category == TicketCategory.legal:
            escalate = True
            escalation_reason = "Legal ticket — always escalated per policy"
            self._log(ticket.ticket_id, ActionType.ESCALATE, escalation_reason)

        elif classification.priority.value in ("p0",):
            escalate = True
            escalation_reason = f"P0 priority ({classification.reasoning[:80]})"
            self._log(ticket.ticket_id, ActionType.ESCALATE, escalation_reason)

        return TriageResult(
            ticket_id=ticket.ticket_id,
            classification=classification,
            retrieved_docs=docs,
            route_to=route_to,
            draft=draft,
            escalated=escalate,
            escalation_reason=escalation_reason,
            actions=self.logger.by_ticket(ticket.ticket_id),
        )

    # -- helpers --------------------------------------------------------------

    def _ensure_kb(self) -> None:
        """Build or load the vector store once."""
        try:
            self._kb.build_or_load()
        except RuntimeError:
            self._log("SYSTEM", ActionType.ERROR, "KB build failed — continuing without retrieval")

    def _log(self, ticket_id: str, action: ActionType, message: str) -> None:
        self.logger.log(ActionLog(
            ticket_id=ticket_id,
            action=action,
            detail={"message": message},
        ))