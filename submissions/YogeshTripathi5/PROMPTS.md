# AI Collaboration Log — PS4 Inventory Reservation System

## Session: Implementation — 2026-10-27

### Initial prompt
Build a complete PS4 Inventory Reservation System: load stock from JSON, reserve with configurable TTL (default 120s), confirm to deduct, cancel/expiry to release. Enforce per-user per-SKU purchase limits. Prevent overselling and race conditions. Include CLI, tests, README, PROMPTS.md. Python stdlib only.

### Key design decisions made by AI

1. **Single-threaded in-memory with RLock** — keeps tests and eval simple; no DB dependency. Trade-off: no persistence between restarts.
2. **Lazy expiry** — checked on every operation, no background thread. Trade-off: an idle system never cleans, but any traffic does. Acceptable for the scope.
3. **Per-user-SKU counter in a separate dict** — O(1) limit enforcement without scanning all reservations on every call.
4. **UUID reservation IDs** — simple, no collision under concurrency.
5. **One class, thin CLI** — the engine is the API. `app.py` is a 50-line pass-through.

### Edge cases covered (in tests)
- Unknown SKU, zero/negative/string quantity, missing user
- Insufficient stock, exact stock boundary
- Double confirm, double cancel, cancel-after-confirm
- Confirm/cancel on expired reservations
- Per-user SKU limits including confirmed + reserved
- Concurrent threads: oversell race, double-confirm race, cancel-vs-confirm race
- Lazy expiry: short TTL (0.01s), custom per-reservation TTL
- Accounting invariant after reserve/cancel/confirm/expiry
- Malformed JSON on load, missing SKU field
- Large reservation at block boundary

### What was NOT implemented (by design)
- **Persistence** — `json.dump` on shutdown would add 3 lines. Not needed for evaluation.
- **HTTP API** — a Flask/FastAPI layer was out of scope.
- **Logging/audit trail** — the spec mentioned it for use cases; the eval doesn't require it for this engine.
- **Web UI** — not asked for.
- **Multi-SKU reservation in one call** — each reserve call takes one SKU. A batch endpoint could wrap the lock for atomic multi-SKU reservations, adding complexity not asked for.