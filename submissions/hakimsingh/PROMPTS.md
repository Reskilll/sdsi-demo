# PROMPTS.md — AI Collaboration Effectiveness

> Exact prompts fed to the AI coding assistant (Claude Code) to produce this
> solution, plus one-line design-rationale annotations.

---

## Prompt 1 — Problem framing

```
You are building PS4: Inventory Reservation System (Flash Sale) for an...
[full problem statement with M1-M5, quality bar, and edge cases]
```

**Why:** Gave the agent the full eval rubric upfront so it could optimize for
the right dimensions (edge cases, cleanliness, concurrency, docs) from the
first line of code rather than requiring a later refactor.

---

## Prompt 2 — Atomic reserve detail

> (Embedded in Prompt 1 as the "Crux: the atomic reserve" section)

**Why:** The single most error-prone part of the solution is the race condition
on reserve. Spelling out the exact six-step protocol (validate, compute
available, reject-if-exceeds, reject-if-over-user-limit, create, update
counters) inside a single lock ensured the agent never wrote a
check-then-act pattern.

---

## Prompt 3 — Eager + lazy expiry

> (Embedded in Prompt 1)

```
Implement both lazy checks (on read/confirm/report) and an eager background
sweeper thread...
```

**Why:** A purely lazy expiry could mean a cancelled TTL holds stock until
someone happens to read a report. A purely eager sweeper has a gap between
real expiry and the next sweep tick. Doing both is what a production system
needs; it also demonstrates security-conscious design.

---

## Key design decisions (inline annotations)

| Decision | Rationale |
|----------|-----------|
| Single `threading.RLock` | Simpler than per-SKU locks; no deadlock risk; correct for single-process. |
| All-or-nothing reserve | No partial reservations — cleaner semantics and avoids split-race bugs. |
| `_reconcile_user_state` on first access | Prevents silent drift if counters ever desync (belt-and-suspenders). |
| Custom exception hierarchy | Lets the CLI catch `InventoryError` at the top level while tests assert on exact subclasses. |
| `new_id()` = `uuid4().hex[:16]` | Short, URL-safe, ID collision astronomically unlikely; no DB needed. |
| Stdlib-only | Zero-dependency score; `pytest` is the only dev dependency. |
| Sweeper on a daemon thread | Graceful shutdown via `stop_sweeper()` + `threading.Event`. |
| Lazy expiry on `_get_active_reservation` | Catches the confirm-after-expiry case without waiting for the sweeper. |

---

## What I'd add with more time (stretch)

- FastAPI web layer wrapping the engine (routes, req/resp models, HTTP errors).
- Load test script hammering reserve concurrently with assertions.
- JSON audit log of every state transition.
- Prometheus-style counters exported via a simple HTTP endpoint.
- Atomic file-load (read + parse + validate under 10 MB limit = already done).