# PS4 — Inventory Reservation System (Flash Sale)

Prevent overselling during a flash sale. A thread-safe, lock-guarded inventory
reservation engine written in pure Python (stdlib only).

## State Model

```
Product (loaded from inventory.json, immutable)
  └─ ProductState (runtime counters: total, reserved, sold)
       └─ derived: available = total - reserved - sold

Reservation (mutable state machine)
  active ──confirm──→ confirmed
  active ──cancel───→ cancelled
  active ──expires──→ expired  (via lazy check or background sweeper)
```

**Core invariant (never violated):** `reserved + sold <= total`

Per-user-per-SKU counters track each user's held + confirmed quantity to
enforce the `per_user_limit`.

## Structure

```
submissions/ps4/
├── __init__.py
├── __main__.py          # Demo CLI — python -m submissions.ps4
├── errors.py            # Exception hierarchy
├── loader.py            # Load & validate inventory.json
├── models.py            # Dataclasses: Product, ReservationRecord, etc.
├── service.py           # InventoryReservationEngine — the core
├── reporting.py         # Pretty-print helpers
├── inventory.json       # Sample data
├── requirements.txt     # pytest only
├── .gitignore
├── README.md
├── PROMPTS.md
└── tests/
    ├── __init__.py
    └── test_inventory.py  # All milestones + edge cases + concurrency
```

## Quick start

```bash
# Run tests
cd submissions/ps4
pip install pytest
pytest -v

# Run demo
python -m submissions.ps4
```

Or from the repo root:

```bash
pytest submissions/ps4/tests/ -v
python -m submissions.ps4
```

## API

| Method               | What it does                          |
|----------------------|---------------------------------------|
| `reserve(sku, user, qty)` | Atomically reserve units (returns id + expires_at) |
| `confirm(id)`        | Permanent deduction (reserved → sold) |
| `cancel(id)`         | Release reservation (reserved → available) |
| `report([sku])`      | Snapshot of available/reserved/sold/total |

All methods are thread-safe thanks to a single `threading.RLock`.

## Scaling to production

This implementation uses in-process dicts and a mutex. For a real flash sale
(non-trivial traffic, multi-instance):

- **Redis** — `INCR` for stock decrements, Lua scripts for atomic
  reserve-confirm, `EXPIRE` for TTLs, sorted sets for per-user limits.
- **Database** — row-level locks (`SELECT ... FOR UPDATE`) on a product row,
  reservation table with a background cron for expiry.

## Edge cases covered

- Two users race for the last unit → exactly one wins.
- Reserve over available stock → `InsufficientStockError`, no change.
- Reserve over per-user limit → `PerUserLimitError`, no change.
- Zero/negative/non-integer qty → `InvalidDataError`.
- Unknown SKU / empty user / malformed file → clear error messages.
- Expiry at boundary → counts as expired.
- Confirm after cancel / cancel after confirm → `InvalidTransitionError`.
- Memory bounded: expired/cancelled reservations soft-cleaned by sweeper.
- `reserved + sold <= total` invariant checked after every operation.