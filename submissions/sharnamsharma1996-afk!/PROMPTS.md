# AI Collaboration Prompts — Flash-Sale Inventory Reservation

## Problem statement
> Prevent overselling during a flash sale. Reserve stock for users with a
> TTL, confirm to permanently deduct, cancel/TTL-expiry to release. Enforce
> per-user purchase limits per SKU. Report available, reserved, and sold
> counts.

## Prompt log

### 1. Initial brief analysis
**Prompt:** *"Review the use-case brief and the existing scaffold repo.
Propose architecture: stdlib-only Python, library + CLI, lazy TTL sweep,
thread-safe lock, atomic file persistence."*

**AI response:** The AI confirmed Python was a good fit given the `agent.py`
scaffold and the evaluator environment, then offered 2 decisions: directory
alias and CLI-vs-HTTP interface. I chose `sharnamsharma1996-afk!` and CLI.

### 2. Core library: reservation.py
**Prompt:** (implicit from the architecture decision) *"Write the core
InventorySystem with dataclass types, TTL sweep, per-user limits, and
atomic JSON persistence."*

**AI response:** Delivered `reservation.py` with all required operations,
typed exceptions, thread-safe locking, and lazy expiry. Auto-pushed an
edit to remove a stale variable from an early draft.

### 3. CLI layer: cli.py
**Prompt:** (implicit) *"Write an argparse CLI wrapping the library with
subcommands for load/reserve/confirm/cancel/report/list/summary."*

**AI response:** Delivered `cli.py` with clean subcommand dispatch and
`--state` override for the persistence file.

### 4. Tests: tests.py
**Prompt:** (implicit) *"Write a comprehensive test suite covering M1–M5,
edge cases (race conditions, expiry, double-ops, auth), and persistence
round-trips. Make it runnable standalone."*

**AI response:** Delivered `tests.py` with 25+ test cases including a
20-thread race-condition test and state-persistence round-trip.

### 5. Documentation: README.md + PROMPTS.md
**Prompt:** (implicit) *"Write README with quick-start, CLI reference,
architecture decisions, and edge-case coverage. Write PROMPTS.md logging
AI collaboration."*

**AI response:** Delivered both files.

## Key architectural decisions made with AI

| Decision | Rationale |
|---|---|
| **Lazy TTL sweep** | Avoids background daemon threads; simpler, correct |
| **Single coarse lock** | Good enough for a CLI tool; no deadlock risk |
| **Atomic file writes** | Write tmp → rename prevents data loss |
| **Unguessable IDs** | `secrets.token_hex` — cryptographically random |
| **Aggregate limit check** | Confirmed + active = true liability |
| **Product reload clears state** | Prevents stale reservations from surviving a product config change |

## What AI caught / refined

- **Duplicate-SKU detection** in `load_products` — I didn't explicitly ask for it.
- **Negative stock/per-user-limit validation** — caught in JSON parsing.
- **Race-condition test** with 20 threads — AI proposed it proactively.
- **`_load()` sweep bug** — AI removed a `self._sweep()` call that ran before the lock was held; deferred to first public access.
- **Re-load after persistence test** (products don't persist, only state) — AI caught the subtlety and wrote the test correctly.