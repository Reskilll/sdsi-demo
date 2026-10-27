# Flash-Sale Inventory Reservation System

Prevent overselling during a flash sale. Reserve stock with a TTL,
confirm to permanently deduct, cancel to release, with per-user purchase
limits.

**Zero dependencies** — standard-library Python 3.9+ only.

## Quick start

```bash
# 1. Load product inventory
python cli.py load inventory.json

# 2. Reserve 1 PS5 for user alice (120 s TTL)
python cli.py reserve alice PS5
# ✓ Reserved — ID: rsv_a1b2c3d4...

# 3. Confirm the reservation (permanently deducts stock)
python cli.py confirm rsv_a1b2c3d4... --user alice

# 4. Or cancel to release stock back
python cli.py cancel rsv_a1b2c3d4... --user alice

# 5. See stock report
python cli.py report
# SKU       Name                 Total  Available  Reserved   Sold
# PS5       PlayStation 5           10          9         0      1
# AIRPODS   AirPods Pro             50         50         0      0
# ...

# 6. Full summary (report + reservations)
python cli.py summary
```

## CLI reference

| Command | Description |
|---|---|
| `load <path>` | Load products from inventory.json |
| `reserve <user> <sku> [qty] [--ttl N]` | Reserve stock (default qty=1) |
| `confirm <id> [--user <user>]` | Confirm reservation |
| `cancel <id> [--user <user>]` | Cancel reservation |
| `report [sku]` | Stock report (all or one SKU) |
| `list [--user <user>]` | List reservations |
| `summary` | Report + reservations |

## Inventory file format

```json
{
  "config": { "reservation_ttl_seconds": 120 },
  "products": [
    { "sku": "PS5", "name": "PlayStation 5", "total_stock": 10, "per_user_limit": 1 },
    { "sku": "GIFT_CARD", "name": "$50 Gift Card", "total_stock": 500, "per_user_limit": 0 }
  ]
}
```

- `per_user_limit: 0` means no limit.
- `config.reservation_ttl_seconds` overrides the default 120 s.

## Architecture

```
cli.py          — argparse-based CLI
reservation.py  — core library (thread-safe InventorySystem)
tests.py        — pytest-compatible test suite (also runs standalone)
inventory.json  — sample product data
state.json      — auto-created persistence file (auto-saved on every mutation)
```

### Design decisions

| Decision | Why |
|---|---|
| **Lazy TTL sweep** | No background threads; expired reservations are cleaned at access time. Safe, simple, deterministic. |
| **Thread-safe single lock** | All mutations go through `threading.Lock`. Correct under contention without deadlock risk. |
| **Unguessable reservation IDs** | `rsv_` + `token_hex(10)` — 80 bits of entropy, resistant to enumeration. |
| **Atomic file saves** | Write-to-tmp-then-rename; never corrupts state on crash. |
| **Per-user limit = confirmed + active** | Prevents a user from reserving beyond their limit even before confirming. |
| **Zero external deps** | stdlib-only — runs anywhere Python 3.9+ is installed. |

### Edge cases covered

- Race: 20 concurrent threads for last item — only stock count succeeds
- TTL boundary: confirm after expiry rejected
- Double confirm / cancel-after-confirm rejected
- Wrong-user confirm/cancel rejected
- Negative/zero quantities, empty user-ids
- Duplicate SKUs in inventory file
- Malformed JSON, missing files
- State persistence across CLI invocations with expired-reservation sweep on reload

## Testing

```bash
# With pytest
pytest tests.py -v

# Standalone (no deps)
python tests.py
```

## Requirements

Python 3.9+. Nothing else.