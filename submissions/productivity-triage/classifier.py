"""Classifier — uses an LLM via LangChain to classify a ticket into a category,
assign priority, and return a confidence score."""

from __future__ import annotations

import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CONFIDENCE_THRESHOLD,
)
from models import Ticket, ClassificationResult, TicketCategory, TicketPriority


CLASSIFY_SYSTEM_PROMPT = """You are a document & ticket triage classifier.
Analyze the ticket and output a single JSON object with these keys:

- category: one of [bug, feature_request, question, complaint, spam, billing, account, legal, service_outage, unknown]
- priority: one of [p0, p1, p2, p3, p4]
- confidence: float between 0.0 and 1.0 (how sure you are about the category)
- reasoning: one-sentence explanation of your decision

Classification rules:
- bug: a defect, malfunction, or error in the product (P0 if data-loss or security, P1 if a core workflow is broken)
- feature_request: asking for new or changed functionality (P3 or P4)
- question: how-to, clarification, or informational question (P3)
- complaint: dissatisfaction with the product or company (P2)
- spam: unsolicited or promotional content (P4)
- billing: payment, invoice, refund, pricing (P2)
- account: access, password-reset, profile changes (P2)
- legal: legal threats, GDPR, compliance (P1)
- service_outage: the service is down or unreachable (P0)
- unknown: cannot determine confidently

PRIORITY GUIDE:
- P0: data loss, security breach, service-down
- P1: high impact, legal, no workaround
- P2: medium impact (billing, account issues)
- P3: low impact, questions, feature requests
- P4: informational, spam

Only output the JSON object, no other text."""


class Classifier:
    """LLM-powered ticket classifier built on LangChain."""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm or ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

    # -- public API -----------------------------------------------------------

    @property
    def threshold(self) -> float:
        return CONFIDENCE_THRESHOLD

    def classify(self, ticket: Ticket) -> ClassificationResult:
        """Return the classification for *ticket*.

        On any parsing failure we return a low-confidence 'unknown' result
        so the pipeline escalates it to a human.
        """
        chain = self._llm | StrOutputParser()
        messages = [
            SystemMessage(content=CLASSIFY_SYSTEM_PROMPT),
            HumanMessage(content=self._ticket_text(ticket)),
        ]
        raw = chain.invoke([m.model_dump() for m in messages])
        return self._parse(raw, ticket.ticket_id)

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _ticket_text(ticket: Ticket) -> str:
        return f"SUBJECT: {ticket.subject}\n\nBODY:\n{ticket.body}"

    @staticmethod
    def _parse(raw: str, ticket_id: str) -> ClassificationResult:
        # Strip markdown fences the LLM may add
        json_str = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        json_str = re.sub(r"\s*```$", "", json_str)

        try:
            data = json.loads(json_str)
            return ClassificationResult(
                category=TicketCategory(data.get("category", "unknown")),
                priority=TicketPriority(data.get("priority", "p3")),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=str(data.get("reasoning", "")),
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            # LLM produced unparseable output → escalate
            return ClassificationResult(
                category=TicketCategory.unknown,
                priority=TicketPriority.p3,
                confidence=0.0,
                reasoning=f"Failed to parse LLM output for ticket {ticket_id}. Raw: {raw[:200]}",
            )