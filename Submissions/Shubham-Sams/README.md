# 🔥 Flash Sale Inventory Reservation System

Prevent overselling during flash sales with TTL-based stock reservations,
per-user purchase limits, and thread-safe inventory tracking.

**Zero external dependencies — Java 21 stdlib only.**

## Quick Start

```bash
# JDK 21+ required
# On Unix:
bash build.sh

# On Windows:
build.bat

# Run the demo
java -jar out/flash-sale.jar demo

# Run tests
java -ea -cp out/classes:out/test-classes com.flashsale.TestRunner   # Unix
java -ea -cp "out/classes;out/test-classes" com.flashsale.TestRunner # Windows
```

## What It Does

1. **Load** products from `inventory.json`
2. **Reserve** stock for a user — hold has a TTL (default 120s)
3. **Confirm** permanently deducts stock; **Cancel** / TTL expiry releases it back
4. **Enforce** per-user purchase limits per SKU (counts active + confirmed)
5. **Report** `available`, `reserved`, and `sold` counts for any SKU or all

## CLI Usage

```bash
java -jar out/flash-sale.jar reserve alice SHOE-RED-42 2
java -jar out/flash-sale.jar status <reservation-id>
java -jar out/flash-sale.jar confirm <reservation-id>
java -jar out/flash-sale.jar cancel  <reservation-id>
java -jar out/flash-sale.jar report [sku]
java -jar out/flash-sale.jar purge
java -jar out/flash-sale.jar demo
```

Options: `--inventory <path>` (default `inventory.json`), `--ttl <seconds>` (default 120).

## Architecture

```
src/main/java/com/flashsale/
├── InventoryStore.java    # Core engine — synchronized, thread-safe
├── InventoryException.java# Typed exceptions (OutOfStock, PerUserLimit, etc.)
├── Json.java              # Zero-dep JSON parser (stdlib only)
├── Product.java           # Product model with guarded counters
├── Reservation.java       # Reservation model with TTL lifecycle
├── ReservationStatus.java # Enum: ACTIVE, CONFIRMED, CANCELLED, EXPIRED
├── StockReport.java       # Immutable report record
└── cli/
    └── ReservationCli.java# CLI (argparse-style command dispatch)

src/test/java/com/flashsale/
└── TestRunner.java        # 54 tests — zero external test framework
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **`synchronized` on store** | Write-heavy flash-sale workloads; single lock avoids deadlock and is fast |
| **Lazy TTL expiry** | No background thread — expired on next access to product |
| **Computed `available()`** | `stock - reserved - sold` — derived from guarded counters, never drifts |
| **Stock check before limit check** | Warehouse-empty is more fundamental than per-user limits |
| **Zero dependencies** | Custom JSON parser; manual test runner — runs on any JDK 21+ |
| **`UUID.random()` hex IDs** | Unique, URL-safe, 12-char — short enough to type |
| **`AtomicInteger` + `synchronized`** | Double protection — `AtomicInteger` for the counters, `synchronized` for the compound operations |

### Inventory JSON Format

```json
{
  "products": [
    {
      "sku": "SHOE-RED-42",
      "name": "Red Running Shoes",
      "description": "Limited edition",
      "price": 2999.00,
      "stock": 100,
      "max_per_user": 2
    }
  ]
}
```

## Testing

```bash
java -ea -cp out/classes:out/test-classes com.flashsale.TestRunner
```

### 54 Tests Across 11 Categories

| Category | Tests | What it covers |
|---|---|---|
| Loading | 9 | valid, missing file, bad JSON, empty, missing field, dup SKU, neg stock/price, zero limit |
| Reserve happy | 5 | basic, multi-user, multi-SKU, custom TTL, unique IDs |
| Reserve edges | 6 | exact stock, exceeds, partial excess, zero/neg qty, unknown SKU |
| Per-user limits | 6 | reserve, confirmed, cancel, expiry, per-SKU, per-user isolation |
| Confirm | 5 | deduct, unknown, double-confirm, cancelled, expired |
| Cancel | 3 | release, unknown, double-cancel |
| TTL expiry | 5 | lazy on reserve/report, purge count, status preserved, limit released |
| Status | 4 | active, unknown, after confirm, after cancel |
| Report | 4 | single SKU, all, invariant, unknown SKU |
| Concurrency | 3 | no oversell (20T×3qty on 50 stock), no double-confirm, limits under contention |
| Lifecycle | 4 | full flow, SKU isolation, never negative, invariant always holds |

## Edge Cases Handled

- **Race conditions** — `synchronized` blocks prevent interleaved read-modify-write
- **Double-confirm** — idempotency guard; second call gets `ReservationNotFound`
- **Expired-confirm** — expiry check inside the lock; expired reservations fail confirm
- **Per-user limit across states** — counts active reservations + confirmed purchases
- **TTL release → re-reserve** — expired stock returns to available; user limit freed
- **Stock check ordering** — out-of-stock fires before per-user limit for large requests

## Requirements

- Java 21+ (uses virtual threads, records, pattern matching)
- Zero external dependencies