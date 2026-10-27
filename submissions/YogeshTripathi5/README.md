# PS4 Inventory Reservation System

A thread-safe inventory reservation engine built for the SDSI Agentic AI Hackathon. Manages the full lifecycle: **reserve → confirm/cancel → expire**.

## Quick start

```bash
cd submissions/YogeshTripathi5
python app.py products
```

## Setup

No dependencies beyond Python 3.8+ standard library.

```bash
# Verify
python --version
```

## Usage

```bash
# List all products
python app.py products

# Show one product
python app.py product PS4-CONSOLE

# Reserve stock (user_id is any string)
python app.py reserve PS4-CONSOLE alice 2
# → {"success": true, "reservation_id": "uuid-here", "expires_in_seconds": 120}

# Confirm (purchase) a reservation
python app.py confirm <reservation_id>

# Cancel a reservation
python app.py cancel <reservation_id>

# Look up a reservation
python app.py reservation <reservation_id>
```

## Running tests

```bash
python -m unittest test_reservation_system -v
```

## Design

### Architecture

A single class `InventoryReservationSystem` holds all state in-memory. Inventory loads from `inventory.json` on init. The class is the authoritative state machine — the CLI (`app.py`) is a thin pass-through.

### State transitions

```
reserve() → "active" ──confirm()──→ "confirmed"
                       ──cancel()──→ "cancelled"
                       ──expires──→  "expired"
```

Idempotency: confirm/cancel on a reservation already in that state returns `{success: false, error: "already ..."}`.

### Concurrency

A single `threading.RLock` (reentrant lock) wraps every public method. All mutating operations first run lazy expiry (`_clean_expired`) inside the lock. This prevents:

- **Overselling** — reserve checks available stock atomically
- **Double-processing** — confirm checks `active` state atomically, only one thread wins
- **Race conditions** — concurrent reserve/cancel/confirm on the same SKU serialise

### Expiry

Lazy, checked on every mutating call and every product/reservation read. No background timers. A short TTL in tests (0.01s) demonstrates expiry works. Default TTL is 120s.

### Accounting guarantee

Every product's `total`, `reserved`, `sold`, `available` columns satisfy:

```
available = total - reserved - sold
```

Reserve increments `reserved`. Confirm moves `reserved → sold`. Cancel/expiry decrements `reserved`. The invariant is checked by assertions and by `test_accounting_consistency`.

### Purchase limits

Per-user, per-SKU counter tracks the sum of active reservations + confirmed purchases. Limits are enforced atomically inside the lock.

## Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| In-memory (dict) | Database | Zero dependencies, atomic within lock. Data lost on restart — acceptable for hackathon eval. |
| `threading.RLock` | asyncio / multiprocessing | Simpler, same correctness for thread concurrency. Fine for a demo with concurrent requests. |
| Lazy expiry | Timer/background thread | No timer overhead, no leak risk. A long-idle system with no calls will not clean up, but a system with any traffic will. |
| UUID strings | Integer sequence | Unguessable, no collision under concurrent reservation. |
| Per-limit tracked via separate dict | Scan reservations per-call | O(1) lookup vs O(n). Slight memory overhead for user-SKU keys that's freed on release. |

## Files

| File | Purpose |
|---|---|
| `reservation_system.py` | Core engine — public API, thread-safe, state machine |
| `app.py` | CLI wrapper |
| `inventory.json` | Product/stock seed data |
| `test_reservation_system.py` | Tests — unit, edge, concurrency |
| `PROMPTS.md` | AI collaboration log |