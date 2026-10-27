"""Pydantic data models for the triage agent."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TicketCategory(str, Enum):
    bug = "bug"
    feature_request = "feature_request"
    question = "question"
    complaint = "complaint"
    spam = "spam"
    billing = "billing"
    account = "account"
    legal = "legal"
    service_outage = "service_outage"
    unknown = "unknown"


class TicketPriority(str, Enum):
    p0 = "p0"   # data loss / security / critical outage
    p1 = "p1"   # high impact, no workaround
    p2 = "p2"   # medium impact
    p3 = "p3"   # low impact / cosmetic
    p4 = "p4"   # informational / feature request


class ActionType(str, Enum):
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    ROUTE = "route"
    DRAFT = "draft"
    ESCALATE = "escalate"
    DISCARD = "discard"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------

class Ticket(BaseModel):
    """An incoming document or support ticket."""
    ticket_id: str = Field(description="Unique ticket identifier")
    subject: str = Field(description="Ticket subject line", min_length=1)
    body: str = Field(description="Full ticket body", min_length=1)
    sender_email: Optional[str] = Field(default=None, description="Sender's email address")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the ticket was received",
    )


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    """Output of the classification step."""
    category: TicketCategory = Field(description="Classified ticket category")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model confidence in the classification (0–1)",
    )
    priority: TicketPriority = Field(description="Inferred ticket priority")
    reasoning: str = Field(description="Brief explanation of the classification decision")


# ---------------------------------------------------------------------------
# RAG retrieval result
# ---------------------------------------------------------------------------

class RetrievedDocument(BaseModel):
    """A document chunk retrieved from the knowledge base."""
    content: str
    source: str
    relevance_score: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Draft response
# ---------------------------------------------------------------------------

class DraftResponse(BaseModel):
    """First-response draft for human review."""
    to: str
    subject: str
    body: str
    policies_referenced: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Action log entry
# ---------------------------------------------------------------------------

class ActionLog(BaseModel):
    """One logged action."""
    ticket_id: str
    action: ActionType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detail: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Final triage result (the return value of agent.run)
# ---------------------------------------------------------------------------

class TriageResult(BaseModel):
    """Complete result from the triage pipeline."""
    ticket_id: str
    classification: ClassificationResult
    retrieved_docs: list[RetrievedDocument] = Field(default_factory=list)
    route_to: Optional[str] = None
    draft: Optional[DraftResponse] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    actions: list[ActionLog] = Field(default_factory=list)