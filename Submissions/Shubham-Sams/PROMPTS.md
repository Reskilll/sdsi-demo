# PROMPTS.md — AI Collaboration Effectiveness

## Problem Statement

Build an **Inventory Reservation System** for flash sales that:
- Loads products from a JSON file (M1)
- Reserves stock with TTL (default 120s) (M2)
- Confirms permanently deducts; cancel/TTL expiry releases (M3)
- Enforces per-user purchase limits per SKU (M4)
- Reports available, reserved, and sold counts (M5)
- Handles concurrency, edge cases, and is production-quality

## Environment Constraint

Maven could not download dependencies (SSL cert issue in the environment).
**Solution**: Rewrote everything as zero-dependency Java — custom JSON parser
replacing Jackson, hand-rolled test runner replacing JUnit. Runs on JDK 21+ only.

---

## Prompt Log

### Prompt 1 — Initial Python Build

**Prompt:**
> "Build a flash sale inventory system. Prevent overselling. TTL holds, per-user limits. Act as senior dev with 10+ years."

**AI Response:** Built full Python solution (stdlib only, 45 tests, CLI + demo).

### Prompt 2 — Switch to Java

**Prompt:**
> "develop code in java because is already present in system"

**AI Response:** Rebuilt everything in Java. Java 25 available on this machine.

**Key adaptations:**
- `synchronized` instance methods for thread safety (replaces Python `threading.Lock`)
- `record` for `StockReport` (immutable data carrier)
- `AtomicInteger` for Product's reserved/sold counters
- Virtual threads via `Thread.ofPlatform()` for concurrency tests
- Custom JSON tokenizer/parser (~130 lines) replaces Jackson
- Hand-rolled test runner with assertion helpers replaces JUnit

### Prompt 3 — Build & Debug Cycle

**Issues found and fixed during compilation:**
1. **Jackson removed** — wrote `Json.java` parser from scratch (objects, arrays, strings, numbers, booleans, null, escape sequences)
2. **JUnit removed** — wrote `TestRunner.java` with custom assert methods and dot-output runner
3. **String parser eats whitespace** — `t.advance()` skips whitespace even inside quoted strings; added `rawAdvance()` for in-string character-by-character advance
4. **Number parser whitespace in substring** — `t.advance()` skipped whitespace between digits and end-of-line; switched to raw `t.pos++` and explicit `skipWhitespace()` after
5. **Stock-before-limit check order** — requests larger than stock + max_per_user got PerUserLimit instead of OutOfStock; swapped check order

---

## Key Design Decisions

| # | Decision | Why |
|---|----------|-----|
| 1 | `synchronized` on all public mutators | Simplest correct concurrency — no deadlock risk |
| 2 | Lazy TTL expiry | No background thread; expired on next access |
| 3 | `available()` computed, never stored | `stock - reserved - sold` — can never drift |
| 4 | Stock check before limit check | "Warehouse empty" precedes "user limit" |
| 5 | Per-user limit = active + confirmed | Prevents hoarding via multiple concurrent holds |
| 6 | Custom JSON parser | Maven couldn't download Jackson — fits in 130 lines |
| 7 | Custom test runner | No JUnit available — 54 tests pass with dot-output |
| 8 | `build.bat` + `build.sh` scripts | Cross-platform; no Maven/Gradle needed |

## Collaboration Summary

- **Total prompts**: 2 core prompts + 1 debug cycle
- **AI role**: Architect, implementer, tester, debugger
- **Human role**: Problem definition, environment constraint feedback
- **Lines of production code**: ~650 (InventoryStore, Product, Reservation, Json, CLI, exceptions, models)
- **Lines of test code**: ~500 (TestRunner — 54 test cases, 11 categories)
- **Test results**: 54 passed, 0 failed
- **External dependencies**: 0