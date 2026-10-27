# AI Collaboration Log — PROMPTS.md

## Initial Design

### Prompt
> I want you to develop a URL shortener with: shorten (custom alias, expiry) into Base62 6-8 chars, resolve with 302/410/404, validate http/https only, block javascript: schemes, same URL returns same short code, stats (total clicks, clicks per day, last accessed).

### AI Decision
Built a modular three-layer architecture:
1. `database.py` — SQLite with WAL mode, parameterised queries
2. `shortener.py` — pure domain logic, no UI dependency
3. `app.py` — Streamlit frontend

### Rationale
- Separate concerns so the core logic is testable without Streamlit
- WAL mode for concurrent read safety
- Parameterised queries from the start to prevent SQL injection

### Extra Edge Cases Identified by AI
- URL normalisation (trailing slashes, default ports, case folding)
- Reserved word blocking for aliases
- Loopback / localhost rejection
- Unicode URL handling
- `data:`, `file:`, `ftp:`, `vbscript:` scheme blocking
- Empty/whitespace-only input
- Zero and negative expiry values
- Custom alias collision detection
- Exhausted code space (fallback from 6→7→8 chars)

## Streamlit Decision

### Prompt
> We will be using python and streamlit for the frontend. What do you think?

### AI Decision
Agreed — Streamlit provides a fast UI with minimal code. Designed a single-page app with three tabs: Shorten, Resolve/Stats, Dashboard.

### Rationale
Streamlit's form widgets and built-in HTML escaping simplify validation and prevent XSS without extra effort.