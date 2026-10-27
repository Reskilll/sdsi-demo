"""Configuration for the Document & Ticket Triage Agent."""

import os
from pathlib import Path

# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parent
KB_DIR = BASE_DIR / "kb"
LOG_DIR = BASE_DIR / "logs"

# ---- LLM Configuration ----
# Uses LangChain with OpenAI-compatible model.
# Set OPENAI_API_KEY or equivalent in env; defaults to gpt-4o-mini.
LLM_MODEL = os.environ.get("TRIAGE_LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.environ.get("TRIAGE_LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.environ.get("TRIAGE_LLM_MAX_TOKENS", "1024"))

# ---- Embedding / RAG ----
EMBEDDING_MODEL = os.environ.get(
    "TRIAGE_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
)
CHUNK_SIZE = int(os.environ.get("TRIAGE_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("TRIAGE_CHUNK_OVERLAP", "50"))
RETRIEVAL_K = int(os.environ.get("TRIAGE_RETRIEVAL_K", "5"))
FAISS_INDEX_PATH = BASE_DIR / "faiss_index"

# ---- Classification ----
CONFIDENCE_THRESHOLD = float(os.environ.get("TRIAGE_CONFIDENCE_THRESHOLD", "0.70"))

# ---- Routing ----
CATEGORY_ROUTING = {
    "bug":                  "engineering-team",
    "feature_request":      "product-team",
    "question":             "support-team",
    "complaint":            "customer-success-team",
    "spam":                 None,               # silently discard
    "billing":              "finance-team",
    "account":              "support-team",
    "legal":                "legal-team",
    "service_outage":       "sre-team",
}

# ---- Logging ----
LOG_FILE = LOG_DIR / "triage.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(action)s | ticket=%(ticket_id)s | %(message)s"