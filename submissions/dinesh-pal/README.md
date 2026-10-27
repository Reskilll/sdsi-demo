# Inventory Reservation System — Flash Sale Engine

Production-grade in-memory flash-sale reservation engine with **zero external dependencies** (no Redis, no MySQL).
Built with per-SKU granular locking, TTL-based expiry, per-user purchase limits, idempotency keys, and a
background sweeper — all written in pure Python with `threading.RLock`.

```
┌──────────┐   POST /reserve ──►  ┌────────────────┐   POST /confirm ──►  ┌──────┐
│  Client  │                       │  Reservation    │                      │ SOLD │
│          │                       │  Engine         │                      └──────┘
└──────────┘                       │  (In-Memory)    │
                                   │                 │   POST /cancel ──►  ┌──────────┐
                                   │  Per-SKU Lock   │                      │ RELEASED │
                                   │  TTL Worker     │                      └──────────┘
                                   └────────────────┘
```

## Quick Start

```bash
cd submissions/dinesh-pal

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python -m src.main

# 3. Play with the API
curl -X POST http://localhost:8000/reserve \
  -H "Content-Type: application/json" \
  -d '{"sku":"SNEAKER-X99","user_id":"alice","quantity":1}'

curl http://localhost:8000/report/SNEAKER-X99
```

Server starts at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reserve` | Reserve stock (M2). Returns `reservation_id` with TTL. |
| `POST` | `/confirm` | Confirm reservation → permanent stock deduct (M3). Idempotent. |
| `POST` | `/cancel` | Cancel reservation → release stock back (M3). Idempotent. |
| `GET` | `/report/{sku}` | Real-time counters for one SKU (M5). |
| `GET` | `/report` | Real-time counters for all SKUs (M5). |
| `GET` | `/reservation/{id}` | Look up a reservation by ID. |
| `GET` | `/health` | Liveness check. |

All mutating endpoints accept an optional `idempotency_key` field for safe client-side retries.

### Example: Full lifecycle

```bash
# 1. Reserve
RESP=$(curl -s -X POST http://localhost:8000/reserve \
  -H "Content-Type: application/json" \
  -d '{"sku":"SNEAKER-X99","user_id":"alice","quantity":1,"idempotency_key":"order-001"}')
RID=$(echo $RESP | python -c "import sys,json; print(json.load(sys.stdin)['reservation_id'])")

# 2. Complete the purchase
curl -X POST http://localhost:8000/confirm \
  -H "Content-Type: application/json" \
  -d "{\"reservation_id\":\"$RID\",\"idempotency_key\":\"order-001-confirm\"}"

# 3. Or cancel
# curl -X POST http://localhost:8000/cancel ...

# 4. Check stock
curl http://localhost:8000/report/SNEAKER-X99
```

## Architecture

### Module Layout

```
submissions/dinesh-pal/
├── inventory.json          # Sample product data + config
├── requirements.txt        # Python dependencies
├── src/
│   ├── models.py           # Immutable dataclasses, enums, config
│   ├── store.py            # Thread-safe in-memory store (RLock per SKU)
│   ├── engine.py           # Orchestration layer (load inventory, start sweeper)
│   ├── sweeper.py          # Background daemon thread for TTL expiry
│   ├── schemas.py          # Pydantic request/response validation
│   ├── app.py              # FastAPI REST layer
│   └── main.py             # CLI entry point (uvicorn)
└── tests/
    ├── test_core.py        # 39 unit + concurrency tests
    └── test_api.py         # 15 FastAPI integration tests
```

### Lock Strategy

```
StateStore
├── _locks_lock: Lock              # guards _locks dict creation only
├── _locks: Dict[str, RLock]       # ONE reentrant lock per SKU
├── _skus: Dict[str, _MutableSku]  # guarded by _locks[sku]
│   ├── product: Product           # immutable
│   ├── sold: int
│   ├── reservations: Dict[str, _MutableReservation]
│   └── user_held: Dict[str, int]  # per-user "currently held" counter
└── _idempotency: Dict             # guarded by _idempotency_lock
```

**Why per-SKU locks**: Two shoppers fighting over the last SNEAKER-X99
compete on one lock — the winner reserves, the loser gets `INSUFFICIENT_STOCK`.
Meanwhile, a PHONE-Z5 reservation proceeds on a *different* lock, completely
unblocked. The sweeper acquires one SKU lock at a time, so the main path
is never starved waiting for expiry.

### State Machine

```
  ┌──────────┐   confirm()    ┌──────┐
  │ RESERVED ├──────────────► │ SOLD │  (terminal, idempotent)
  └────┬──▲──┘                └──────┘
       │  │
       │  │ cancel() / expire_stale()
       │  │
       v  │
  ┌──────────┐
  │ RELEASED │  (terminal, idempotent)
  └──────────┘
```

- RESERVED → SOLD: `confirm()` under SKU lock, increments `sold`, decrements `user_held`
- RESERVED → RELEASED: `cancel()` or sweeper, decrements `user_held`
- SOLD → SOLD: idempotent confirm (returns existing record)
- RELEASED → RELEASED: idempotent cancel
- RELEASED → SOLD: ❌ rejected (already released)
- SOLD → RELEASED: ❌ rejected (already sold)

### TTL & Clock Drift

All TTL comparisons use Python's `time.monotonic()` — a clock that never goes
backward, immune to NTP adjustments and daylight savings. The sweeper runs in a
daemon thread with configurable interval (default 1 s). It walks all SKUs,
acquires each lock briefly, and releases any reservation where
`expires_at <= now`. The sleeper thread uses small-slice `event.wait(0.1)` so
shutdown is responsive.

## Performance Rationale

| Choice | Why |
|--------|-----|
| Per-SKU `RLock` | Maximises throughput — unrelated SKUs never contend. |
| `time.monotonic()` | Immune to clock drift (NTP, DST). |
| Daemon sweeper thread | Expiry never blocks the request path. |
| `uuid4` reservation IDs | Collision-free without a central sequencer. |
| Frozen dataclass snapshots | Thread-safe reads — callers can't mutate internal state. |
| Pydantic validation | Malformed JSON never reaches the engine — fails fast at 422. |

## Hidden Edge Cases Handled

| Edge Case | How |
|-----------|-----|
| **Zero oversell** | Stock check + reservation creation is atomic under the SKU lock. |
| **Double-confirm** | State machine: SOLD→SOLD is idempotent (returns existing record, doesn't double-deduct). |
| **Double-cancel** | RELEASED→RELEASED is idempotent. |
| **Confirm after cancel** | RELEASED state rejects transition → RESERVATION_ALREADY_TERMINAL error. |
| **Cancel after confirm** | SOLD state rejects → RESERVATION_ALREADY_TERMINAL error. |
| **Limit check timing** | `user_held` includes active RESERVED entries; checked under the SKU lock. |
| **Limit freed by cancel** | `_release_reservation` decrements `user_held`. |
| **Limit freed by confirm** | SOLD reservations don't count toward held limit. |
| **TTL expiry vs confirm race** | Both acquire the same SKU lock; exactly one wins. |
| **Idempotency replay** | Cached (success, payload) tuples prevent double-creation on retry. |

## Running Tests

```bash
cd submissions/dinesh-pal

# Run everything (54 tests: 39 core + 15 API)
python -m pytest tests/ -v

# Core + concurrency only
python -m pytest tests/test_core.py -v

# API only
python -m pytest tests/test_api.py -v
```

## Configuration

Edit `inventory.json` for product catalog. The `config` block overrides defaults:

```json
{
  "config": {
    "reservation_ttl_seconds": 120,
    "sweeper_interval_seconds": 1.0,
    "idempotency_ttl_seconds": 86400
  }
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `reservation_ttl_seconds` | 120 | How long a reservation is held before expiry. |
| `sweeper_interval_seconds` | 1.0 | How often the sweeper scans for expired reservations. |
| `idempotency_ttl_seconds` | 86400 | How long idempotency keys are cached (24 h). |

## License

MIT — built for the SDSI Agentic AI Hackathon.