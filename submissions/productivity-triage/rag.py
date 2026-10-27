"""RAG module — builds a FAISS vector store from policy documents and retrieves
relevant chunks for a given ticket."""

from __future__ import annotations

import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from config import (
    KB_DIR,
    FAISS_INDEX_PATH,
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RETRIEVAL_K,
)
from models import RetrievedDocument


class KnowledgeBase:
    """Wraps a FAISS vector store over policy documents for RAG retrieval."""

    def __init__(
        self,
        kb_dir: Path | None = None,
        index_dir: Path | None = None,
    ) -> None:
        self._kb_dir = kb_dir or KB_DIR
        self._index_dir = index_dir or FAISS_INDEX_PATH
        self._embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"trust_remote_code": True},
        )
        self._vectorstore: FAISS | None = None

    # -- public API -----------------------------------------------------------

    def build_or_load(self) -> FAISS:
        """Build index from scratch (or load cached).

        If FAISS_INDEX_PATH exists on disk we load it; otherwise we ingest
        every .txt file in *kb_dir* and persist the index for the next run.
        """
        if os.path.isdir(str(self._index_dir)):
            self._vectorstore = FAISS.load_local(
                str(self._index_dir),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            self._vectorstore = self._build_index()
        return self._vectorstore

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedDocument]:
        """Return the top-*k* most relevant chunks for *query*."""
        if self._vectorstore is None:
            raise RuntimeError("KnowledgeBase not built — call build_or_load() first")

        k = k or RETRIEVAL_K
        docs_with_scores = self._vectorstore.similarity_search_with_relevance_scores(
            query, k=k
        )
        return [
            RetrievedDocument(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                relevance_score=round(score, 4),
            )
            for doc, score in docs_with_scores
        ]

    # -- internals ------------------------------------------------------------

    def _build_index(self) -> FAISS:
        loader = DirectoryLoader(
            str(self._kb_dir),
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"autodetect_encoding": True},
        )
        raw_docs = loader.load()
        if not raw_docs:
            raise RuntimeError(
                f"No .txt documents found in {self._kb_dir}. "
                "Add policy files and retry."
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(raw_docs)

        vectorstore = FAISS.from_documents(chunks, self._embeddings)
        vectorstore.save_local(str(self._index_dir))
        return vectorstore