"""Tests for the KnowledgeBase (RAG) module.

These tests actually build a FAISS index from the sample_policies.txt,
so they depend on sentence-transformers being installed.
"""

import os
import tempfile
from pathlib import Path

import pytest

from rag import KnowledgeBase
from models import RetrievedDocument


@pytest.fixture
def kb() -> KnowledgeBase:
    """Return a KnowledgeBase pointed at the sample policies."""
    return KnowledgeBase()


@pytest.fixture
def built_kb(kb: KnowledgeBase) -> KnowledgeBase:
    """Build (or load cached) the KB once for all tests."""
    kb.build_or_load()
    return kb


class TestKnowledgeBase:

    def test_build_or_load_returns_faiss(self, kb: KnowledgeBase):
        vs = kb.build_or_load()
        # FAISS vectorstore has a 'search' method
        assert hasattr(vs, "similarity_search_with_relevance_scores")

    def test_retrieve_without_build_raises(self, kb: KnowledgeBase):
        # Create a fresh KB that hasn't been built
        # Use a temp index dir to guarantee it's not cached
        with tempfile.TemporaryDirectory() as tmp:
            fresh = KnowledgeBase(index_dir=Path(tmp))
            with pytest.raises(RuntimeError, match="not built"):
                fresh.retrieve("refund policy")

    def test_retrieve_returns_documents(self, built_kb: KnowledgeBase):
        docs = built_kb.retrieve("How do refunds work?", k=3)
        assert len(docs) >= 1
        assert all(isinstance(d, RetrievedDocument) for d in docs)
        # At least one doc should mention "refund"
        contents = " ".join(d.content.lower() for d in docs)
        assert "refund" in contents

    def test_retrieve_relevance_order(self, built_kb: KnowledgeBase):
        """First result should be most relevant."""
        docs = built_kb.retrieve("service outage SRE immediate response", k=5)
        assert len(docs) >= 1
        scores = [d.relevance_score for d in docs]
        # Scores should be non-increasing (first one highest or equal)
        assert scores[0] >= scores[-1]

    def test_retrieves_policy_for_bug(self, built_kb: KnowledgeBase):
        docs = built_kb.retrieve("critical security vulnerability data leak P0", k=5)
        contents = " ".join(d.content.lower() for d in docs)
        assert "p0" in contents or "bug" in contents or "security" in contents

    def test_retrieves_policy_for_billing(self, built_kb: KnowledgeBase):
        docs = built_kb.retrieve("I was overcharged on my invoice", k=5)
        contents = " ".join(d.content.lower() for d in docs)
        assert "billing" in contents or "refund" in contents or "finance" in contents

    def test_retrieves_policy_for_legal(self, built_kb: KnowledgeBase):
        docs = built_kb.retrieve("GDPR data export request", k=5)
        contents = " ".join(d.content.lower() for d in docs)
        assert "gdpr" in contents or "legal" in contents or "compliance" in contents

    def test_k_respected(self, built_kb: KnowledgeBase):
        for k in [1, 3, 5]:
            docs = built_kb.retrieve("outage", k=k)
            assert len(docs) <= k