"""Retriever — lightweight helper that fetches relevant documents from the KB
for a given query. Separate from the full KB class to keep concerns isolated."""

from __future__ import annotations

from models import RetrievedDocument
from rag import KnowledgeBase


def retrieve_context(
    kb: KnowledgeBase,
    query: str,
    k: int = 5,
) -> list[RetrievedDocument]:
    """Return top-*k* policy documents relevant to *query*.

    This is the canonical retrieval entry-point used by both the drafter
    and any future reasoning steps.
    """
    return kb.retrieve(query, k=k)