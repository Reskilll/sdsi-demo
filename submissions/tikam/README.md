# URL Shortener — SDSI Digithon 2026

A fast, secure URL shortener with a Streamlit frontend. Built for the SDSI Agentic AI Digithon 2026 Developer Track.

## Features

- **Shorten URLs** — generates 6–8 character Base62 short codes
- **Custom aliases** — choose your own (4–32 chars, a-z A-Z 0-9 `-` `_`)
- **Auto-expiry** — set link expiry in hours (up to 1 year)
- **Idempotent** — same URL always returns the same short code (unless a custom alias is given)
- **Resolve** — HTTP 302 (found), 410 (expired), 404 (not found)
- **Stats** — total clicks, clicks per day, last-accessed time
- **Dashboard** — browse all shortened URLs with click counts

## Security

- Only `http://` and `https://` schemes allowed
- Blocks `javascript:`, `data:`, `file:`, `ftp:`, `vbscript:` schemes
- Rejects localhost / loopback addresses
- Parameterised SQL queries — no SQL injection
- Input length limits on URLs (2048 chars) and aliases (32 chars)
- Reserved words blocked for aliases (`admin`, `api`, `stats`, …)
- Streamlit auto-escapes HTML output — no XSS

## Project Structure

```
submissions/tikam/
├── app.py              # Streamlit UI
├── shortener.py        # Core business logic (pure domain, no UI)
├── database.py         # SQLite layer with WAL mode
├── test_shortener.py   # 43 unit tests
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── PROMPTS.md          # AI collaboration log
```

---

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **pip** — comes with Python

Verify your installation:

```bash
python --version
pip --version
```

---

## Step-by-Step Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/sdsi-demo.git
cd sdsi-demo
```

### 2. Create a virtual environment (recommended)

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r submissions/tikam/requirements.txt
```

> **Note:** This installs `streamlit>=1.60.0`. If you also want to run tests, install pytest:
> ```bash
> pip install pytest
> ```

### 4. Run the application

```bash
streamlit run submissions/tikam/app.py
```

Open your browser and go to **http://localhost:8501**

### 5. Use the app

| Tab | What you can do |
|---|---|
| **🔗 Shorten URL** | Enter a URL, optionally set a custom alias and expiry (hours), click "Shorten" |
| **🔍 Resolve / Stats** | Enter a short code to simulate a redirect (Found/Expired/Not Found) or view click statistics |
| **📊 Dashboard** | Browse all shortened URLs with click counts and metadata |

### 6. Run the tests

```bash
cd sdsi-demo
python -m pytest submissions/tikam/test_shortener.py -v
```

Expected output: **43 passed**

---

## API / Domain Logic

```python
from shortener import shorten, resolve, get_stats

# Shorten a URL
result = shorten("https://example.com/long-url", custom_alias="my-link", expiry_hours=48)
# → {"short_code": "my-link", "original_url": "...", "normalized_url": "...", ...}

# Resolve a short code (simulates HTTP redirect behaviour)
result = resolve("my-link")
# → {"status": "found", "url": "https://example.com/long-url"}     # HTTP 302
# → {"status": "expired", "expires_at": "..."}                      # HTTP 410
# → {"status": "not_found"}                                         # HTTP 404

# Get click statistics
stats = get_stats("my-link")
# → {"total_clicks": 42, "clicks_per_day": {"2026-10-27": 15}, "last_accessed": "..."}
```

---

## Design Decisions

| Decision | Why |
|---|---|
| Base62 | URL-safe, no ambiguous characters, compact |
| SQLite | Zero setup, file-based, WAL for concurrent reads |
| WAL mode | Allows concurrent reads while a write is in progress |
| Idempotent shorten | Consistent UX — same URL → same code |
| Custom alias collision | Explicit error, not silent overwrite |
| Normalised URLs | `example.com` and `example.com/` are treated as the same URL |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `streamlit: command not found` | Make sure your virtual environment is activated, or use `python -m streamlit run ...` |
| `ModuleNotFoundError: No module named 'shortener'` | Run the app from the **repo root** (`sdsi-demo/`), not from inside `submissions/tikam/` |
| Port 8501 already in use | Run with a different port: `streamlit run submissions/tikam/app.py --server.port 8502` |
| Permission denied (PowerShell) | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` then re-activate venv |