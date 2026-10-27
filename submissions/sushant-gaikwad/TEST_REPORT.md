# Test Report — PS4 Flash Sale Inventory

**Date:** 2026-10-27 · **Environment:** Windows 11, JDK 25 (compiled for Java 21), Maven 3.10

**Summary:** all M1–M5 requirements work. 73/73 automated tests pass, 36/37 live API checks pass,
and the load simulation shows no overselling in any run. The one live check that didn't pass was blocked
by the test machine's network filter before it reached the app (see the note in section 2).

| Level | Result |
|---|---|
| Automated tests (`mvn test`) | ✅ 73 passed, 0 failed |
| Live API checks ([`scripts/api_check.sh`](scripts/api_check.sh)) | ✅ 36 passed, ⚠️ 1 blocked by environment |
| Flash-sale simulation, 5,000 buyers × 3 SKUs | ✅ No overselling |

## 1. Automated tests: 73 passed, 0 failed

`mvn clean package`: `BUILD SUCCESS` in about 17 s.

| Suite | Tests | Result |
|---|---|---|
| ConcurrencyTest (repeated runs) | 16 | ✅ |
| HttpApiTest (real HTTP) | 8 | ✅ |
| InventoryLoaderTest | 15 | ✅ |
| InventoryServiceTest: Reserve | 11 | ✅ |
| InventoryServiceTest: ConfirmAndCancel | 7 | ✅ |
| InventoryServiceTest: Expiry | 6 | ✅ |
| InventoryServiceTest: Idempotency + general | 7 | ✅ |
| InventoryServiceTest: PerUserLimit | 3 | ✅ |

## 2. Live API checks: 36 of 37 passed

The packaged jar was started with `data/inventory.json`, and [`scripts/api_check.sh`](scripts/api_check.sh) sent
real HTTP requests to it. Counts are shown as available/reserved/sold.

| Requirement | Check | Result |
|---|---|---|
| **M1** Load file | All 5 SKUs loaded from `inventory.json` | ✅ |
| **M2** Reserve + TTL | Reserving 2 PHONE-X1 gives `ACTIVE` | ✅ |
| | The default hold is exactly 120 s | ✅ |
| | Counts after reserving are 98/2/0 | ✅ |
| **M3** Confirm | Confirm gives `CONFIRMED`; counts become 98/0/2 | ✅ |
| | Confirming twice is safe (200, no double deduction) | ✅ |
| | A confirmed order can't be cancelled (409) | ✅ |
| **M3** Cancel | Cancel releases stock: WATCH-S5 back to 50/0/0 | ✅ |
| | A cancelled hold can't be confirmed (409) | ✅ |
| **M3** TTL expiry | A 3 s hold showed 9/1/0, then 10/0/0 after expiry with no request involved | ✅ |
| | Confirming after expiry gives `410 RESERVATION_EXPIRED` | ✅ |
| **M4** Per-user limit | A user who already bought 2 of 2 is blocked (409) | ✅ |
| | A single request over the limit is blocked (409) | ✅ |
| | Other users are not affected (201) | ✅ |
| **M5** Report | PHONE-X1 shows 96/2/2, which adds up to the 100 total | ✅ |

### Edge cases and security

| Case | Response | Result |
|---|---|---|
| Out of stock | 409 | ✅ |
| Unknown SKU | 404 | ✅ |
| Quantity 0, −1, `"1"` (text) | 400 | ✅ |
| Quantity = 2,147,483,647 (no integer overflow) | 409 | ✅ |
| TTL 0 | 400 | ✅ |
| Unknown field (`"price":0`) | 400 | ✅ |
| Malformed JSON | 400 | ✅ |
| Missing user | 401 | ✅ |
| `<script>` as the user id | 400 | ✅ |
| Viewing another user's reservation | 404 | ✅ |
| Body larger than 4 KB | 413 | ✅ |
| Wrong HTTP method / unknown path | 405 / 404 | ✅ |
| Same `Idempotency-Key` sent twice | Only one hold | ✅ |
| **300 parallel HTTP buyers for 10 units** | Exactly 10 succeeded, 290 rejected, final 0/10/0 | ✅ |
| `../../etc/` path traversal in the URL | Connection reset (no response) | ⚠️ |

**About the ⚠️ check.** Requests containing `../../etc/` were reset before they reached the app; the server
logged nothing. Similar paths without that pattern got normal responses, and the same request text also failed
on a URL that doesn't exist at all. Something on the test machine, most likely antivirus web protection, is
blocking it. The attack is still stopped, and the automated test `unknownOrMalformedIds` confirms the app itself
rejects such ids with `400 INVALID_INPUT`.

## 3. Flash-sale simulation: 5,000 buyers per run

Command: `java -jar target/flash-sale-inventory.jar simulate --sku <SKU> --buyers 5000`. Each buyer reserves 1
unit, then confirms (70%), cancels (20%) or abandons the hold (10%).

| SKU | Stock | Sold | Held | Available | Rejected | Time | Oversold? |
|---|---|---|---|---|---|---|---|
| TAB-S9 | 10 | 9 | 0 | 1 | 4,987 | 259 ms | ✅ No |
| PHONE-X1 | 100 | 73 | 13 | 14 | 4,890 | 310 ms | ✅ No |
| WATCH-S5 | 50 | 37 | 7 | 6 | 4,948 | 233 ms | ✅ No |

In every run, available + held + sold equals the stock, and sales never went above it. Some units are left
available because simulated buyers cancelled after the rush had already ended.

## How to reproduce

```bash
mvn clean package                                              # 73 tests + builds the jar
java -jar target/flash-sale-inventory.jar serve --port 8080    # terminal 1
bash scripts/api_check.sh                                      # terminal 2, needs a freshly started server
java -jar target/flash-sale-inventory.jar simulate --sku TAB-S9 --buyers 5000
```

## Verdict

The submission meets M1–M5 and handles the edge cases. It also held up under 5,000 simultaneous buyers.
There are no code defects outstanding.
