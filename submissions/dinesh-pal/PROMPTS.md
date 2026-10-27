# PROMPTS.md — AI Collaboration Log

## How I built this system

This document records the prompts and iterative refinements used to build the
Inventory Reservation System.  Each section mirrors a logical commit boundary.

---

## Commit 1: Scaffold — models, config, and inventory data

### Prompt
> Create the core data models for an in-memory flash-sale reservation engine
> in Python.  Use frozen dataclasses for value objects, enums for reservation
> state machine, and a `SystemConfig` dataclass for TTL settings.  Also create
> a sample `inventory.json` with at least 3 products.

### Outcome
- `src/models.py`: `Product`, `ReservationRecord`, `SkuReport`, `ReservationState` enum, `ErrorCode` enum, `SystemConfig`  
- `inventory.json`: SNEAKER-X99 (100 stock, limit 2), PHONE-Z5 (50, limit 1), WATCH-A1 (200, limit 3)

---

## Commit 2: Thread-safe state store with per-SKU locks

### Prompt
> Implement `StateStore` — a thread-safe in-memory store with one `threading.RLock` per SKU.
> Methods: `load_products()`, `reserve()`, `confirm()`, `cancel()`, `report_sku()`, `report_all()`,
> `expire_stale()`, `get_reservation()`.  All mutating methods return `(bool, payload)`.
> The sweeper method `expire_stale()` walks all SKUs and releases expired RESERVED entries.
> Include idempotency-key support via a separate lock-guarded dict.

### Outcome
- `src/store.py`: Complete `StateStore` with internal `_MutableSku` and `_MutableReservation`
- Lock strategy: `_locks_lock` protects the lock-dict creation; each SKU gets its own `RLock`
- Idempotency: stores `(success, payload)` tuples keyed by client-supplied key, with TTL

### Key decision
Chose per-SKU locks over a global lock because flash sales concentrate traffic on one SKU,
and we don't want a PHONE-Z5 purchase to block a WATCH-A1 purchase.

---

## Commit 3: Background TTL sweeper

### Prompt
> Write a `Sweeper` class that runs as a daemon thread, calling `store.expire_stale()`
> on a configurable interval.  Use `threading.Event` for clean shutdown.  The sleep
> loop should use small-slice `event.wait()` so shutdown is responsive under 0.5 s.
> Use `time.monotonic()` everywhere — never `time.time()` — for TTL comparisons.

### Outcome
- `src/sweeper.py`: `Sweeper` with `start()`, `stop()`, daemon thread, responsive shutdown

---

## Commit 4: ReservationEngine orchestration

### Prompt
> Write `ReservationEngine` — a thin orchestration layer that owns a `StateStore` and
> a `Sweeper`.  It parses `inventory.json` (merging config overrides), starts the sweeper,
> and delegates all reservation operations to the store.  This is the public API for the
> HTTP layer.

### Outcome
- `src/engine.py`: `ReservationEngine` with `load_inventory()`, `start_sweeper()`, `stop()`,
  and delegation methods for `reserve()`, `confirm()`, `cancel()`, `report_*()`, `get_reservation()`

---

## Commit 5: FastAPI REST API with Pydantic validation

### Prompt
> Build a FastAPI application with the following endpoints: `POST /reserve`, `POST /confirm`,
> `POST /cancel`, `GET /report/{sku}`, `GET /report`, `GET /reservation/{id}`, `GET /health`.
> Use Pydantic `BaseModel` for request validation (field-level constraints, custom validators).
> Wiring uses a module-level engine singleton initialised in the lifespan handler.
> All endpoints accept optional `idempotency_key`.

### Outcome
- `src/schemas.py`: `ReserveRequest`, `ConfirmCancelRequest`, `CancelRequest`, response models
- `src/app.py`: `create_app()` factory, lifespan handler, all 7 routes, error-to-HTTP-status mapping
- `src/main.py`: CLI entry point with uvicorn

---

## Commit 6: Unit tests — core logic

### Prompt
> Write pytest tests for M1–M5: product loading, reserve (happy path + all error modes),
> confirm/cancel (including state machine transitions), user limit enforcement,
> real-time reports.  Each test class uses a helper `_new_engine()` that creates
> a temp inventory file and a fresh engine.

### Outcome
- `tests/test_core.py`: 39 tests across `TestProductLoading`, `TestReserve`, `TestConfirm`,
  `TestCancel`, `TestUserLimits`, `TestReports`

---

## Commit 7: Concurrency tests — zero oversell proof

### Prompt
> Write concurrency tests using `threading.Thread`:
> 1. 50 threads reserve 1 unit each from 30 available → exactly 30 succeed
> 2. 50 threads confirm the same reservation → sold count is original qty, not 50×qty
> 3. 20 threads cancel the same reservation → stock released exactly once
> 4. Two threads both try to reserve the full per-user limit → only one succeeds
> 5. TTL expiry + new reservation race → correct available count

### Outcome
- `tests/test_core.py`: `TestConcurrency` with 5 concurrent test methods
- Critical invariant: `available + reserved + sold == total_stock` per SKU after all tests

---

## Commit 8: Idempotency tests

### Prompt
> Verify idempotency keys: same key returns same success result (same reservation_id,
> same user, same quantity); same key returns same error; different keys are independent;
> confirm idempotency works too.

### Outcome
- `tests/test_core.py`: `TestIdempotency` with 4 tests

---

## Commit 9: API integration tests

### Prompt
> Write 15 FastAPI integration tests using `httpx.AsyncClient` with `ASGITransport`.
> Test every endpoint: health, reserve (success, insufficient stock, unknown SKU,
> validation), confirm, cancel, reports, idempotency, reservation lookup.

### Outcome
- `tests/test_api.py`: 15 tests, all async, fixture creates a fresh app with test store

---

## Commit 10: TTL expiry tests

### Prompt
> Set TTL=0.05 s and verify: sweeper releases expired reservations, expired
> reservations cannot be confirmed, expired holds free the user's limit slot.

### Outcome
- `tests/test_core.py`: `TestTTLExpiry` with 3 tests

---

## Commit 11: Edge cases and cleanup

### Prompt
> Test: total_stock=0 rejects all reservations, monotonic clock invariants,
> sweeper start/stop cycle, unknown SKU report returns None.

### Outcome
- `tests/test_core.py`: `TestEdgeCases` with 5 tests
- Total: 54 tests, 100% pass rate

---

## Commit 12: Documentation and polish

### Prompt
> Write README.md with quick-start, API reference, architecture diagrams,
> lock strategy rationale, performance notes, edge-case table, and test-running
> instructions.  Write PROMPTS.md with commit-by-commit AI collaboration log.

### Outcome
- `README.md`, `PROMPTS.md` (this file)

---

## Git Commit Structure Suggestion

```
git checkout -b dinesh-pal

# Each of these is a clean, reviewable commit:
git add src/models.py inventory.json && git commit -m "feat: add data models and sample inventory"
git add src/store.py && git commit -m "feat: implement thread-safe StateStore with per-SKU locks"
git add src/sweeper.py && git commit -m "feat: add background TTL sweeper daemon"
git add src/engine.py && git commit -m "feat: add ReservationEngine orchestration layer"
git add src/schemas.py src/app.py src/main.py && git commit -m "feat: add FastAPI REST layer with Pydantic validation"
git add tests/test_core.py && git commit -m "test: add 39 unit + concurrency tests"
git add tests/test_api.py && git commit -m "test: add 15 API integration tests"
git add README.md PROMPTS.md && git commit -m "docs: add README, architecture docs, and AI collaboration log"

# Then push and open a PR
git push origin dinesh-pal
```

Each commit tells a story: models → store → sweeper → engine → API → tests → docs.
A reviewer can follow the architecture evolving one concern at a time.