# PROMPTS.md — PS4 Inventory Reservation System

This file documents how Claude Code was used to build this submission and how
its output was reviewed and corrected.

## Iteration 1 — Problem breakdown

**Prompt:**
> Analyse this problem statement and list every must-have, edge case, and
> implicit requirement. Think from the evaluator's perspective: what hidden
> tests would expose an incomplete solution?

**AI output:** Enumerated M1–M5 and 23 edge cases covering inventory loading,
reserve/confirm/cancel lifecycle, per-user limits, TTL mechanics, input
validation, and sanitization.

**Correction:** The AI initially missed that per-user limits should be enforced
at *reserve* time counting both confirmed and reserved quantities, not at
confirm time. This was corrected — counting only confirmed would let a user
stack reservations and confirm them all, violating the purchase cap.

## Iteration 2 — Architecture design

**Prompt:**
> Design a fast, secure architecture for this flash-sale reservation system.
> Constraints: no database, no network, no eval, Python stdlib only. The
> evaluator reads code but doesn't run it — tests ARE the evidence. What data
> structures and locking strategy prevent oversell?

**AI output:** Recommended an in-memory `ReservationSystem` class with
`threading.RLock`, computed available (not stored), per-SKU lazy expiry, and
an injectable clock for tests.

**Correction:** The AI initially suggested a per-SKU lock. We simplified to a
single `RLock` — sufficient for the single-JSON-operation-at-a-time contract
and reduces deadlock risk. The available formula was also corrected from
`stock - reserved` (which ignored sold) to `stock - reserved - sold`.

## Iteration 3 — Scaffold and engine

**Prompt:**
> Write the engine.py with full type hints, error taxonomy
> (SystemError/BusinessError), and docstrings. Starting scaffold comment was
> "plan → use tools → produce a result" — "tools" here means internal helper
> functions. Include all validation, sanitization, and the expiry mechanism.

**AI output:** Produced the complete engine with all five actions and internal
helpers. Included `_expire_stale`, `_resolve_reservation` (with user+sku
fallback), strict `_validate_*` helpers rejecting bools-as-ints.

**Correction:** The engine originally placed `_expire_stale` at the *end* of
confirm rather than before the status check — a subtle bug where a just-expired
reservation could still be confirmed. Fixed: expire before checking `r.status
is RESERVED`.

## Iteration 4 — Edge case tests

**Prompt:**
> Write unittest tests covering all must-haves and every edge case listed
> above. Use a FakeClock. Keep tests readable — each test method should test
> exactly one thing.

**AI output:** Generated test_engine.py with 27 test methods.

**Correction:** Three tests were initially missing:
1. TTL expiry restoring available (M3c).
2. Cancelling then re-reserving (M4 limit released).  
3. The large-inventory smoke test (E20).

These were added in a follow-up pass.

## Iteration 5 — Run contract and agent.py

**Prompt:**
> Write agent.py — the thin `run(task: str) -> dict` wrapper. Handle parse
> errors (escalated), dispatch to engine, catch BusinessError (rejected, not
> escalated) and SystemError (error, escalated). Include `__main__` for the
> "one run command" README requirement.

**AI output:** Produced agent.py with the three-path dispatch (parse → validate
→ execute), clean error shape, and CLI entry point.

**Correction:** The initial dispatch passed `request.get(...)` without default
for ttl, so `None` would silently become 0. Fixed to `request.get("ttl", 120)`
— the problem statement's default.

## Iteration 6 — Code review pass

**Prompt:**
> `/code-review` — find any correctness bugs, simplifications, or edge case
> gaps in the full submission.

**AI findings:**
- `report` originally sorted items by insertion order → changed to
  alphabetical (`sorted()`).
- `clean_display` didn't handle `None` gracefully → added `str()` fallback.
- `report` with a specific SKU validated only in the `if sku is not None`
  branch — ok but needed a dedicated `_validate_single_identifier` helper.

**All applied.**

## Summary

| Metric | Count |
|--------|-------|
| Prompt iterations | 6 |
| AI corrections applied | 8 |
| Bugs caught by review | 3 |
| Edge cases covered | 23 + must-haves