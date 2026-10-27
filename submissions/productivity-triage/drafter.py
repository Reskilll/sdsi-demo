"""Drafter — uses RAG-retrieved policies + LLM to draft a first-response email
for human review."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, CATEGORY_ROUTING
from models import (
    Ticket,
    ClassificationResult,
    RetrievedDocument,
    DraftResponse,
    TicketCategory,
)

from rag import KnowledgeBase
from retriever import retrieve_context


DRAFT_SYSTEM_PROMPT = """You are a professional support agent drafting a first-response email.
Write a polite, helpful reply that:

1. Acknowledges the ticket
2. References the relevant policy/policies provided to you
3. Sets expectations on next steps or timeline
4. Uses the provided signature

The response MUST be a single JSON object with:
- subject: the email subject (readable, not a raw ticket ID)
- to: the recipient email address
- body: the full email body (plain text)
- policies_referenced: array of policy snippets (copy verbatim from the context)

Only output the JSON object, no other text."""


class Drafter:
    """Drafts first responses using RAG context + LLM."""

    def __init__(
        self,
        kb: KnowledgeBase | None = None,
        llm: BaseChatModel | None = None,
    ) -> None:
        self._kb = kb or KnowledgeBase()
        self._llm = llm or ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

    # -- public API -----------------------------------------------------------

    def build_kb(self) -> KnowledgeBase:
        """Initialise or load the knowledge base once."""
        self._kb.build_or_load()
        return self._kb

    def draft(
        self,
        ticket: Ticket,
        classification: ClassificationResult,
    ) -> DraftResponse:
        """Produce a draft response for *ticket* using retrieved policies.

        Certain categories never get an auto-draft (spam, legal)."""
        if classification.category == TicketCategory.spam:
            return DraftResponse(
                to=ticket.sender_email or "",
                subject=f"Auto: {ticket.subject}",
                body="[SPAM — no response sent]",
            )

        if classification.category == TicketCategory.legal:
            return DraftResponse(
                to=ticket.sender_email or "",
                subject=f"Auto: {ticket.subject}",
                body="[LEGAL — draft withheld; requires human review per policy]",
            )

        # Build retrieval query from ticket content
        query = f"{ticket.subject}\n{ticket.body}"
        docs = retrieve_context(self._kb, query, k=5)

        drafted_body = self._generate(ticket, classification, docs)

        return DraftResponse(
            to=ticket.sender_email or "",
            subject=f"Re: {ticket.subject}",
            body=drafted_body,
            policies_referenced=[d.content.strip() for d in docs],
        )

    # -- internals ------------------------------------------------------------

    def _generate(
        self,
        ticket: Ticket,
        classification: ClassificationResult,
        docs: list[RetrievedDocument],
    ) -> str:
        """Ask the LLM to compose a draft given the ticket + policy context."""
        policy_context = "\n---\n".join(
            f"[Policy from {doc.source} (score={doc.relevance_score})]\n{doc.content}"
            for doc in docs
        )

        team = CATEGORY_ROUTING.get(classification.category.value, "support-team")
        signature = f"Best regards,\n{team}"

        human = (
            f"TICKET SUBJECT: {ticket.subject}\n"
            f"TICKET BODY:\n{ticket.body}\n\n"
            f"CLASSIFICATION: {classification.category.value} "
            f"(confidence={classification.confidence:.2f})\n\n"
            f"RETRIEVED POLICIES:\n{policy_context}\n\n"
            f"SIGNATURE:\n{signature}\n\n"
            f"RECIPIENT: {ticket.sender_email or 'unknown'}"
        )

        chain = self._llm | StrOutputParser()
        messages = [
            SystemMessage(content=DRAFT_SYSTEM_PROMPT),
            HumanMessage(content=human),
        ]

        raw = chain.invoke([m.model_dump() for m in messages])

        # Try to pull body out of JSON; fall back to raw text
        import json
        import re
        json_str = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        json_str = re.sub(r"\s*```$", "", json_str)
        try:
            data = json.loads(json_str)
            return data.get("body", raw)
        except json.JSONDecodeError:
            return raw