# PS4: Inventory Reservation System (Flash Sale) — Md Mobshshir Nayeem (TowardInfinity)

Prevents overselling during a flash sale: stock is loaded from `inventory.json`,
users hold reservations with a TTL (default 120 s), confirm permanently deducts,
cancel/expiry releases, per-SKU per-user purchase limits are enforced cumulatively,
and per-SKU available/reserved/sold counts are reported.

## Run it

Requires: Go 1.25+ (dev only — the program itself is stdlib-only, no network,
no database, no API keys at runtime).

```bash
cd submissions/TowardInfinity
go run ./cmd/inventory-cli -f data/demo-commands.txt
go test -race ./internal/...
```

The first command drives the engine with a scripted flash-sale demo (reserve →
confirm, reserve → cancel, limit rejection, oversell rejection) and prints one
JSON response per command. The second runs the test suite with the race
detector enabled (requires a C toolchain for CGO; plain `go test ./internal/...`
also passes).

Sample output (real run of `demo-commands.txt`, timestamps will differ):

```
{"ok":true,"op":"report","data":[{"sku":"EARBUDS-PRO","name":"Wireless Earbuds Pro","stock":200,"available":200,"reserved":0,"sold":0,"pricePaise":499900,"userLimit":3},{"sku":"PHONE-128-BLK","name":"Smartphone 128GB Black","stock":50,"available":50,"reserved":0,"sold":0,"pricePaise":2999900,"userLimit":2},{"sku":"POWERBANK-20K","name":"Power Bank 20000mAh","stock":10,"available":10,"reserved":0,"sold":0,"pricePaise":149900,"userLimit":1},{"sku":"WATCH-ACTIVE","name":"Smartwatch Active","stock":0,"available":0,"reserved":0,"sold":0,"pricePaise":899900,"userLimit":1}]}
{"ok":true,"op":"reserve","data":{"available":49,"expiresAt":"2026-10-27T05:47:01Z","id":"r1","qty":1,"sku":"PHONE-128-BLK","state":"reserved","user":"u1"}}
{"ok":true,"op":"reserve","data":{"available":48,"expiresAt":"2026-10-27T05:47:01Z","id":"r2","qty":1,"sku":"PHONE-128-BLK","state":"reserved","user":"u1"}}
{"ok":false,"op":"reserve","error":"per-user purchase limit exceeded: sku \"PHONE-128-BLK\" limit 2, already committed 2, requested 1","errorKind":"user-limit"}
{"ok":true,"op":"confirm","data":{"id":"r1","qty":1,"sku":"PHONE-128-BLK","state":"sold","user":"u1"}}
{"ok":true,"op":"cancel","data":{"id":"r2","qty":1,"sku":"PHONE-128-BLK","state":"canceled","user":"u1"}}
{"ok":true,"op":"reserve","data":{"available":9,"expiresAt":"2026-10-27T05:47:01Z","id":"r3","qty":1,"sku":"POWERBANK-20K","state":"reserved","user":"u2"}}
{"ok":false,"op":"reserve","error":"per-user purchase limit exceeded: sku \"POWERBANK-20K\" limit 1, already committed 1, requested 1","errorKind":"user-limit"}
{"ok":false,"op":"reserve","error":"insufficient stock: sku \"WATCH-ACTIVE\" wants 1, has 0","errorKind":"insufficient-stock"}
{"ok":false,"op":"reserve","error":"insufficient stock: sku \"EARBUDS-PRO\" wants 500, has 200","errorKind":"insufficient-stock"}
{"ok":false,"op":"reserve","error":"unknown sku: \"UNKNOWN-SKU\"","errorKind":"unknown-sku"}
{"ok":false,"op":"confirm","error":"reservation id not found: \"does-not-exist\"","errorKind":"unknown-reservation"}
{"ok":true,"op":"report","data":[{"sku":"EARBUDS-PRO","name":"Wireless Earbuds Pro","stock":200,"available":200,"reserved":0,"sold":0,"pricePaise":499900,"userLimit":3},{"sku":"PHONE-128-BLK","name":"Smartphone 128GB Black","stock":50,"available":49,"reserved":0,"sold":1,"pricePaise":2999900,"userLimit":2},{"sku":"POWERBANK-20K","name":"Power Bank 20000mAh","stock":10,"available":9,"reserved":1,"sold":0,"pricePaise":149900,"userLimit":1},{"sku":"WATCH-ACTIVE","name":"Smartwatch Active","stock":0,"available":0,"reserved":0,"sold":0,"pricePaise":899900,"userLimit":1}]}
```

A REST API for live demos is also built in: `go run ./cmd/inventory-cli -serve`
(listens on `127.0.0.1:8080`; `POST /reserve`, `POST /confirm?id=`, `POST /cancel?id=`,
`GET /report`). Smoke-tested end to end:

```
$ curl -s -X POST localhost:8080/reserve -d '{"user":"u1","sku":"PHONE-128-BLK","qty":1}'
{"available":49,"expiresAt":"2026-10-27T05:48:30Z","id":"r1"}
$ curl -s -X POST "localhost:8080/confirm?id=r1"
{"id":"r1","qty":1,"sku":"PHONE-128-BLK","state":"sold","user":"u1"}
$ curl -s -X POST localhost:8080/reserve -d '{"user":"u1","sku":"NOPE","qty":1}'
{"error":"unknown sku: \"NOPE\""}
```

## Input format

```jsonc
{
  "products": [
    {
      "sku": "PHONE-128-BLK",   // required, unique, non-empty
      "name": "Smartphone 128GB Black",
      "stock": 50,              // >= 0
      "userLimit": 2,           // per-user purchase limit per SKU, >= 1
      "pricePaise": 2999900     // exact integer minor units, >= 0 (no floats)
    }
  ]
}
```

Commands (newline-delimited JSON on stdin, or via `-f`):

```jsonc
{"op":"reserve","user":"u1","sku":"PHONE-128-BLK","qty":1}  // hold stock for TTL
{"op":"confirm","id":"r1"}   // permanently deduct; idempotent
{"op":"cancel","id":"r1"}    // release the hold; idempotent
{"op":"get","id":"r1"}       // inspect one reservation
{"op":"report"}              // available/reserved/sold per SKU
```

## Design choices

- **Engine/interface split.** All logic lives in `internal/engine`; the CLI is a
  thin adapter that parses commands and maps errors to messages. The engine is
  UI-agnostic and could be driven by any interface.
- **One mutex, serialized transitions.** Every state change (reserve, confirm,
  cancel, sweep) happens under a single engine mutex, so the nastiest edge cases
  — TTL expiry racing a confirm, concurrent reserves overselling — are
  impossible by construction rather than negotiated at runtime. `go test -race`
  proves no data races. A per-SKU lock stripe would buy more throughput at the
  cost of cross-SKU invariants; with the flash-sale hot-row being one SKU, the
  global lock is the honest, provably-correct choice (see Known gaps).
- **Injectable clock.** TTL tests advance a fake clock instead of sleeping, so
  the suite is fast and deterministic; boundary (exactly-at-expiry = expired) is
  covered.
- **Cumulative limits.** A user's limit counts active holds + confirmed sales
  across separate reservations; cancel/expiry frees quota.
- **Single source of truth for available.** `available = stock − sold − active
  reserved`, recomputed under the lock, so reporting can never double-count
  reserved-then-expired stock.

## Assumptions

- Single process, in-memory state; persistence is out of scope for the PS.
- TTL is a fixed 120 s default (engine accepts any duration; the CLI hard-codes 120 s).
- Reservation IDs are engine-generated (`r1`, `r2`, …) and returned to callers.
- Exactly-at-expiry counts as expired (documented boundary).
- Prices are stored as integer paise to avoid float money math.

## Known gaps

- The global mutex serializes all SKUs; under extreme multi-SKU load a striped
  lock would scale further. Correctness is unaffected.
- No persistence: a restart loses in-flight reservations (acceptable for the PS;
  a write-ahead log would be the first addition).
- The REST layer is a demo convenience, not hardened for the open internet
  (no auth, no rate limiting) — script mode is the tested interface.

## Testing

Table-driven tests cover every must-have and the listed edge cases: invalid
inventory files, unknown SKU, reserve more than available, zero stock, invalid
qty/user/sku, confirm inside TTL, confirm exactly at expiry, expiry release,
cancel idempotency, cumulative limits (across reservations, counting sold,
freeing after cancel, per-user/per-SKU independence), expired-stock reporting,
and three concurrency tests (50-goroutine oversell hammer, confirm/cancel race,
mixed traffic) that assert the `stock = available + reserved + sold` invariant.
Run with `-race` to enable the race detector (requires a C toolchain; plain
`go test ./internal/...` also passes).
