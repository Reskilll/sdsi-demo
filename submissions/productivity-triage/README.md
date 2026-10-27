# Productivity — Document & Ticket Triage Agent

An LLM-powered agent that classifies incoming support tickets, retrieves
relevant policies via RAG, routes to the correct team, drafts a first
response for human review, and escalates low-confidence or high-severity
cases. Every action is logged.

## How it works

```
Incoming Ticket
      │
      ▼
┌──────────────┐
│  Classifier  │  LangChain + LLM → category, priority, confidence
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  RAG / KB    │  FAISS + sentence-transformers → relevant policies
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Router     │  Rule-based → team assignment
└──────┬───────┘
       │
       ├── spam? ──────────► discard (no response)
       │
       ▼
┌──────────────┐
│   Drafter    │  LLM + RAG context → first-response draft
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Escalation  │  confidence < 70%? legal? P0? → human queue
└──────────────┘
       │
       ▼
  TriageResult  ← logged at every step
```

## Project structure

```
submissions/productivity-triage/
├── agent.py            # Main entry point — run(task) / run_batch(tasks)
├── pipeliner.py        # Orchestrates classify → retrieve → route → draft → escalate
├── classifier.py       # LLM classification (LangChain + OpenAI-compatible)
├── rag.py              # FAISS vector store over policy documents
├── retriever.py        # Thin helper: retrieve_context()
├── drafter.py          # First-response draft generator (LLM + RAG)
├── logger.py           # Structured action logger (file + in-memory)
├── config.py           # All configuration constants + env overrides
├── models.py           # Pydantic data models (Ticket, TriageResult, etc.)
├── requirements.txt    # Python dependencies
├── kb/
│   └── sample_policies.txt   # Knowledge-base documents for RAG
├── logs/               # Triage action logs (triage.log)
├── faiss_index/        # Cached FAISS index (auto-generated on first run)
└── tests/
    ├── conftest.py             # Pytest config, integration-test skipping
    ├── test_models.py          # Data model validation
    ├── test_logger.py          # Action logger unit tests
    ├── test_rag.py             # Knowledge base / RAG tests
    ├── test_classifier.py      # Classifier unit + integration tests
    ├── test_drafter.py         # Drafter tests
    ├── test_pipeliner.py       # Pipeline routing + escalation tests
    └── test_agent.py           # Agent entry point tests
```

## Data models

| Model | Purpose |
|---|---|
| `Ticket` | Incoming document with subject, body, sender |
| `ClassificationResult` | Category, priority, confidence, reasoning |
| `RetrievedDocument` | KB chunk with source + relevance score |
| `DraftResponse` | Draft email to/from/subject/body + policies referenced |
| `ActionLog` | Timestamped log entry per pipeline step |
| `TriageResult` | Complete pipeline output (assembles all of the above) |

## Configuration

All config lives in `config.py` and can be overridden via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `TRIAGE_LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `TRIAGE_LLM_TEMPERATURE` | `0.2` | LLM temperature |
| `TRIAGE_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer for KB embeddings |
| `TRIAGE_RETRIEVAL_K` | `5` | Number of KB chunks to retrieve |
| `TRIAGE_CONFIDENCE_THRESHOLD` | `0.70` | Below this → escalate to human |

## Categories, routing, and escalation

| Category | Routes to | Priority | Escalation rule |
|---|---|---|---|
| `bug` | engineering-team | P0–P2 | P0 always escalated |
| `feature_request` | product-team | P3–P4 | — |
| `question` | support-team | P3 | — |
| `complaint` | customer-success-team | P2 | — |
| `spam` | (discarded) | P4 | — |
| `billing` | finance-team | P2 | — |
| `account` | support-team | P2 | — |
| `legal` | legal-team | P1 | **Always** escalated |
| `service_outage` | sre-team | P0 | P0 always escalated |
| `unknown` | — | P3 | **Always** escalated (low confidence) |

**Escalation triggers:**
1. Classification confidence < 70% → human triage queue
2. Category is `legal` → legal + management
3. Priority is `P0` (data loss, security, or outage) → engineering lead + on-call

## Setup & installation

```bash
cd submissions/productivity-triage

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set your LLM API key
export OPENAI_API_KEY="sk-..."
```

## Usage

```python
from agent import run, run_batch
from models import Ticket
import json

# Single ticket as JSON
result = run(json.dumps({
    "ticket_id": "T-001",
    "subject": "Cannot export reports to CSV",
    "body": "Every time I click Export → CSV I get a 500 Internal Server Error. This has been broken since the last update.",
    "sender_email": "user@example.com",
}))

print(f"Category: {result.classification.category.value}")
print(f"Confidence: {result.classification.confidence:.0%}")
print(f"Route to: {result.route_to}")
print(f"Escalated: {result.escalated}")
if result.draft:
    print(f"Draft body: {result.draft.body[:200]}...")

# Batch processing
tasks = [
    json.dumps({"ticket_id": f"T-{i:03d}", "subject": s, "body": b, "sender_email": e})
    for i, (s, b, e) in enumerate([
        ("App crash on login", "Steps: open app, click login, crashes immediately...", "user1@test.com"),
        ("Add dark mode please", "Every other app has dark mode...", "user2@test.com"),
        ("Overcharged invoice", "Invoice shows $499, my plan is $299...", "user3@test.com"),
    ])
]

results = run_batch(tasks)
for r in results:
    print(f"{r.ticket_id}: {r.classification.category.value} → {r.route_to} (escalated={r.escalated})")
```

## Running tests

```bash
# Run unit tests only (no LLM calls)
pytest tests/ -v -m "not integration"

# Run all tests including integration (requires OPENAI_API_KEY)
pytest tests/ -v

# Run a specific test file
pytest tests/test_rag.py -v
pytest tests/test_classifier.py -v -m "not integration"
```

### Test coverage

| Test file | Tests | Type |
|---|---|---|
| `test_models.py` | 10 | Unit — data validation, defaults, bounds |
| `test_logger.py` | 3 | Unit — log writing, retrieval, file persistence |
| `test_rag.py` | 8 | Unit — KB building, retrieval relevance, K parameter |
| `test_classifier.py` | 9 | Unit + Integration — LLM parsing, category accuracy |
| `test_drafter.py` | 4 | Unit + Integration — spam/legal short-circuits, draft generation |
| `test_pipeliner.py` | 10 | Integration — routing, escalation logic, action logging |
| `test_agent.py` | 6 | Integration — entry points, JSON & plain-text input, batch |

## Customising the knowledge base

Add your own `.txt` files to the `kb/` directory. The FAISS index rebuilds
automatically on the first run or whenever you delete the `faiss_index/`
directory.

Each policy should be on its own line, formatted as:
```
POLICY: Description of the policy.
CATEGORY: CategoryName — definition.
ROUTING: Category → team-name.
ESCALATION: Trigger → action.
SIGNATURE: Team — "Signature block text."
```