# PROMPTS.md — AI collaboration log

Tool: **Claude Code** (Opus 5.5) in the Claude desktop app, working directly in the repository.

## 1. Initial prompt

> *(pasted the PS4 problem statement: M1–M5, judging criteria, "edge cases that aren't listed")*
> "This is the problem statement of the Digithon. Check the code cloned from git and give a solution for it."

### What the AI did first
- Looked at the cloned repo. It only had a scaffold (`README.md`, `usecases/`, `agent-template/`).
  The repo README asks for work under `submissions/<alias>/`, so the solution went there.
- Checked the toolchain. Python and Node weren't installed; JDK 25 and Maven 3.10 were. **Java 21 +
  Maven** was chosen so the project builds and runs on this machine.

## 2. Design decisions agreed during the session

| Question | Decision | Why |
|---|---|---|
| How do we guarantee no oversell? | One `ReentrantLock` per SKU; check + decrement in one critical section | Correct and simple; hot SKUs don't block others |
| Who expires holds? | Lazy expiry on every operation **plus** a 1 s background sweeper | Correctness never depends on timer timing |
| Confirm racing TTL expiry? | Expiry check runs under the same lock; `now >= expiresAt` means expired → 410 | Can't confirm stock already given to someone else |
| What counts toward the per-user limit? | Active holds + confirmed purchases | Otherwise a user could hold N, confirm, hold N again |
| Retries / double-click "Buy"? | Optional `Idempotency-Key`, scoped per user | Real flash-sale clients retry on timeouts |
| Someone else's reservation id? | 404, not 403 | Doesn't reveal that the id exists |
| How to test TTL without `sleep`? | Inject `java.time.Clock`; tests use `MutableClock` | Deterministic, fast, exact boundary checks |

## 3. Iterations and corrections (where human/AI review changed the code)

1. **O(n) removal from the expiry heap.** The first draft called `PriorityQueue.remove(hold)` on every
   confirm/cancel, which is O(n) under load. It was changed to *lazy deletion*: the heap skips non-ACTIVE
   entries when polled.
2. **Possible deadlock in the purge.** The idempotent `reserve` holds a `ConcurrentHashMap` bin lock (inside
   `computeIfAbsent`) while it takes the SKU lock. The sweeper's purge first removed idempotency keys
   *while holding* the SKU lock, which is the opposite lock order. Fixed by collecting purgeable records
   under the lock and removing them after releasing it. (There's a comment on this in `expireAll`.)
3. **405 handling.** The first draft used a custom exception subclass that returned 400. It was replaced by
   a proper `METHOD_NOT_ALLOWED(405)` error code.
4. **Loader noise.** A product with a missing SKU also reported a spurious "name" error. The default-name
   logic was fixed so each mistake is reported once.
5. **Int overflow.** `alreadyCommitted + quantity` is computed as `long`. A test reserves
   `Integer.MAX_VALUE` to cover it.
6. **Strict JSON types.** Jackson coerces `"2"` to `2` by default. Quantity/TTL parsing now accepts only real
   JSON integers, and tests cover `"1"`, `1.5` and `true`.
7. **Build environment.** Maven failed with `PKIX path building failed` because something on the machine
   intercepts TLS. It was fixed with `-Djavax.net.ssl.trustStoreType=Windows-ROOT`, which the README
   documents.

## 4. Edge cases the AI was asked to think through (and their tests)

- Reserve the last unit from 2,000 threads at once → exactly `stock` succeed (`ConcurrencyTest`)
- One user firing 500 parallel reserves → still capped at the limit
- Confirm and cancel the same hold at the same time → exactly one wins
- Confirm exactly at `expiresAt` → expired (boundary test)
- Cancel after expiry → harmless, idempotent
- Confirm twice / cancel twice → idempotent
- Quantity 0, negative, `Integer.MAX_VALUE`, string, float, boolean
- TTL 0, negative, over 1 h
- Unknown SKU, wrong-case SKU, blank SKU
- Malformed user id (spaces, `<script>`, >64 chars)
- Path-traversal-looking reservation id
- Duplicate SKUs and duplicate JSON keys in the inventory file, stock as a string, empty file
- Body over 4 KB, unknown JSON fields (`"price": 0`)
- Same idempotency key from 200 threads; same key with a different payload
- Finished reservations purged after retention, but purchases still count toward the limit

## 5. How the output was verified

- `mvn test` → **73 tests, 0 failures**. The concurrency suites are `@RepeatedTest` to catch flaky races.
- The packaged jar was started and exercised with real HTTP calls, and the simulator was run (see the README).
- Every generated file was reviewed before commit. Nothing was accepted without a passing test.
