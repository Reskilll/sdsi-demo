# PS4 — Inventory Reservation System (Flash Sale)

A thread-safe, in-memory reservation engine that **prevents overselling** during a flash sale,
with a JSON REST API, a load simulator, and 73 automated tests.

- Java 21+ · Maven · Jackson (JSON) · JUnit 5. No web framework: the API runs on the JDK's built-in
  `HttpServer` with virtual threads.

## Requirements coverage

| # | Requirement | Where |
|---|---|---|
| M1 | Load products and stock from `inventory.json` | [`InventoryLoader`](src/main/java/com/sdsi/inventory/loader/InventoryLoader.java), [`data/inventory.json`](data/inventory.json) |
| M2 | Reserve stock for a user, held for a TTL (default 120 s) | `InventoryService.reserve` |
| M3 | Confirm permanently deducts; cancel or TTL expiry releases | `confirm`, `cancel`, `expireDue` / `expireAll` + background sweeper |
| M4 | Per-user purchase limit per SKU | checked atomically in `createHold` (active holds + confirmed purchases) |
| M5 | Available / reserved / sold per SKU | `report()`; `GET /inventory` |

Stretch items: REST API, `Idempotency-Key` support for safe retries, a flash-sale load simulator,
structured audit log lines, memory-bounded retention of finished reservations.

## Quick start

```bash
cd submissions/sushant-gaikwad
mvn test                     # run the 73 tests
mvn package -DskipTests      # builds target/flash-sale-inventory.jar
java -jar target/flash-sale-inventory.jar serve --port 8080
```

> If Maven fails with `PKIX path building failed` on Windows (a proxy or antivirus intercepting TLS),
> run with `MAVEN_OPTS="-Djavax.net.ssl.trustStoreType=Windows-ROOT"`.

Options: `--inventory FILE` (default `data/inventory.json`), `--host` (default `127.0.0.1`),
`--port` (default `8080`), `--ttl SECONDS` (default `120`).

### Try it

```bash
curl -s localhost:8080/inventory
curl -s -X POST localhost:8080/reservations -H "X-User-Id: alice" -H "Content-Type: application/json" \
     -d '{"sku":"PHONE-X1","quantity":2}'
curl -s -X POST localhost:8080/reservations/<id>/confirm -H "X-User-Id: alice"
curl -s localhost:8080/inventory/PHONE-X1
```

### Flash-sale simulation

```bash
java -jar target/flash-sale-inventory.jar simulate --sku TAB-S9 --buyers 5000
```

5,000 buyers go for the same SKU at once on virtual threads. Each confirms (70%), cancels (20%) or
abandons the hold (10%). The run prints the outcome and checks `available + reserved + sold == total`
and `sold <= stock`.

## API

The caller is identified by the `X-User-Id` header (1–64 chars of `[A-Za-z0-9_.@-]`). In production
this would come from a verified auth token; see *Security* below.

| Method | Path | Body / headers | Success |
|---|---|---|---|
| GET | `/health` | | 200 |
| GET | `/inventory` | | 200: list of `{sku,name,total,available,reserved,sold,perUserLimit}` |
| GET | `/inventory/{sku}` | | 200 |
| POST | `/reservations` | `{"sku","quantity","ttlSeconds"?}`, optional `Idempotency-Key` | 201: reservation |
| GET | `/reservations/{id}` | | 200 |
| POST | `/reservations/{id}/confirm` | | 200 (idempotent) |
| POST | `/reservations/{id}/cancel` | also `DELETE /reservations/{id}` | 200 (idempotent) |

Errors always look like `{"error":{"code":"...","message":"..."}}`:

| Code | HTTP | When |
|---|---|---|
| `INVALID_INPUT` | 400 | bad JSON, unknown field, non-integer or ≤0 quantity, TTL outside 1–3600 s, bad id |
| `UNAUTHORIZED` | 401 | missing `X-User-Id` |
| `SKU_NOT_FOUND` / `RESERVATION_NOT_FOUND` / `NOT_FOUND` | 404 | unknown SKU, reservation (or someone else's), path |
| `METHOD_NOT_ALLOWED` | 405 | wrong verb |
| `INSUFFICIENT_STOCK` | 409 | not enough available units |
| `PER_USER_LIMIT_EXCEEDED` | 409 | held + bought + requested > limit |
| `INVALID_STATE` | 409 | confirm a cancelled hold, cancel a confirmed one |
| `IDEMPOTENCY_CONFLICT` | 409 | same key reused for a different SKU/quantity |
| `RESERVATION_EXPIRED` | 410 | confirm after TTL |
| `PAYLOAD_TOO_LARGE` | 413 | body over 4 KB |

## Inventory file format

```json
{ "products": [ { "sku": "PHONE-X1", "name": "Galaxy X1", "stock": 100, "perUserLimit": 2 } ] }
```

A bare array also works. `name` defaults to the SKU and `perUserLimit` to 1. The loader rejects
duplicate SKUs, duplicate JSON keys, negative or non-integer stock, strings like `"10"`, limits below 1,
and files over 10 MB. It lists every problem with its index (for example `products[3].stock: must be an
integer`), so a broken file can be fixed in one pass.

## Design

```
HttpApi ──► InventoryService ──► SkuState (one per SKU)
                                   ├─ ReentrantLock
                                   ├─ available / reserved / sold counters
                                   ├─ per-user {held, purchased}
                                   ├─ PriorityQueue of holds by expiresAt
                                   └─ deque of finished holds (for retention purge)
```

**No overselling.** Each SKU has its own lock. The checks "is the user under the limit?" and "is there
stock?" and the decrement happen in one critical section, so two buyers can never both take the last
unit. SKUs don't block each other, so a hot item doesn't slow down the rest of the catalogue.

**Expiry is enforced in two ways.**
1. *Lazy:* every operation on a SKU first expires its overdue holds (`now >= expiresAt`), so results
   are correct even if the timer thread is late or dead.
2. *Eager:* a daemon sweeper runs every second and returns stock from abandoned holds, so `GET /inventory`
   shows it without anyone touching that SKU.

**Confirm vs. expiry race.** Both run under the SKU lock. A confirm that arrives at or after
`expiresAt` sees the hold already expired and gets `410`; it can't confirm stock that was already handed
to the next buyer.

**Per-user limit** counts active holds plus confirmed purchases. Expired or cancelled holds free the
allowance again. Purchases stay counted even after the reservation record is purged.

**Idempotency.** `Idempotency-Key` is scoped per user. `ConcurrentHashMap.computeIfAbsent` makes
concurrent retries with one key create exactly one hold. A failed attempt (for example, out of stock)
doesn't use up the key. Reusing a key with a different payload gets `409`.

**Performance.**
- Reserve, confirm and cancel take O(log n) per SKU (heap insert).
- Expiry takes O(k log n) for k expired holds.
- Confirmed or cancelled holds are lazily skipped in the heap instead of an O(n) `remove`.
- Finished reservations are purged after 1 hour, so memory stays bounded during a long sale.
- In the simulation, 5,000 concurrent buyers finish in well under a second on a laptop.

**Testability.** Time comes from an injected `java.time.Clock`. Tests use a `MutableClock`, so TTL
behaviour (including the exact `expiresAt` boundary) is checked deterministically, with no `sleep`.

## Security and robustness

- Strict input validation in the service, not only in HTTP: allow-listed patterns for user ids, SKUs,
  reservation ids (UUID) and idempotency keys; integer-only quantities; TTL bounds; `long` arithmetic
  for the limit check, so `Integer.MAX_VALUE` can't overflow it.
- Unknown JSON fields are rejected. Request bodies are capped at 4 KB. Jackson nesting and string
  sizes are capped for the inventory file.
- Ownership: users can only see, confirm or cancel their own reservations. Someone else's id returns
  `404`, not `403`, so ids can't be probed.
- Reservation ids are random UUIDs and can't be guessed.
- Internal errors return a generic `500`; stack traces are only logged on the server.
- Binds to `127.0.0.1` by default.
- Known limits (demo scope): `X-User-Id` stands in for real authentication, and there is no rate
  limiting. In production, put the service behind an API gateway with JWT auth and per-user rate limits.

## Tests (73)

| Suite | Covers |
|---|---|
| `InventoryServiceTest` | M2–M5, TTL boundary, expiry after/before confirm, cancel/confirm state machine, ownership, idempotency, limits, retention purge, validation |
| `ConcurrencyTest` | 2,000 threads on 100 units → exactly 100 sold; 500 concurrent reserves by one user → limit holds; confirm-vs-cancel races; concurrent idempotent retries; background sweeper; simulator invariants |
| `InventoryLoaderTest` | sample file, defaults, every malformed-input case, collected error reporting |
| `HttpApiTest` | real HTTP end to end: happy path, error→status mapping, strict body validation, 413, 410, idempotency header, cross-user access |

## Possible next steps

- Persistence (Redis with Lua scripts, or `UPDATE ... WHERE available >= ?` in SQL) to run several
  instances behind a load balancer. The service boundary stays the same.
- A virtual-queue / waiting-room in front of very hot SKUs.
- Metrics (Micrometer/Prometheus) for hold rate, expiry rate and lock wait time.
