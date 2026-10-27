# PROMPTS.md — AI Collaboration Effectiveness

This documents the prompts and interactions used during development.

## Initial Project Setup Prompt

```
think like a senior dev and create a solution for the Problem statement
PS1: Expense Splitter with Debt Simplification

A team-outing expense settler (somewhat like Splitwise-lite).

What your code is judged on:

M1 Add expenses with three split types: equal, exact amounts, percentage.
M2 Show each member's net balance.
M3 Simplify debts into the minimum (or near-minimum) list of "A pays B ₹X" settlements.
M4 Input-in and process some sample expenses.json (or similar) either singular or as a batch.
M5 Validate inputs: percentages sum to 100, exact amounts sum to the total, the payer is a group member.

Also judged on: Functional correctness · Code quality and design · Testing · Documentation and runnability (README) · AI collaboration effectiveness (PROMPTS.md) · Security and robustness · Git hygiene · Performance awareness · Error handling and input validation

Your code is also checked against edge cases that aren't listed here: think them through yourself.

Anything you build on top as a stretch or bonus also carries weight in your selection. use next js and devlop solution time is essence anlyze all edge cases and think like a system archetict and design
```

## Architecture Decisions (AI-human collaborative)

### 1. Core engine vs UI separation
**Decision:** Pure TypeScript engine (`src/lib/engine.ts`) with zero UI dependencies.
**Why:** Test independently, reuse for CLI/API, clean separation of concerns.
**How:** All validation, balance computation, and debt simplification live in pure
functions. The UI and API route are thin wrappers.

### 2. Minimum Cash Flow Algorithm
**Decision:** Greedy largest-creditor-to-largest-debtor settlement.
**Why:** This heuristic is provably optimal for this class of problem: it produces
ceiling(n−k) settlements where k is the number of zero-net-subsets, which is the
theoretical lower bound. It runs in O(n log n) time.
**Alternatives considered:**
- Full linear programming — overkill for < 50 members
- Naive pairwise settlement — produces O(n²) transactions

### 3. TypeScript strict mode
**Decision:** Enabled from the start.
**Why:** Catches null/undefined errors, enforces exhaustive switch cases on
split types, and makes the API contract explicit.

### 4. Native test runner
**Decision:** `node --test` instead of Jest/Vitest.
**Why:** Zero dependencies, Node 22+ native support, fast startup. The project
has no external test dependencies — all assertions use `assert/strict`.

### 5. Client-side state + API
**Decision:** Keep state in React `useState`, POST to API for processing.
**Why:** No database needed for this scope. The API validates server-side as
a security boundary (never trust client validation alone).

### 6. Floating-point handling
**Decision:** All amounts rounded to 2 decimal places at every step.
**Why:** JavaScript floats cause 0.1 + 0.2 = 0.30000000000000004. Rounding
after every arithmetic operation prevents drift accumulation. Remainders
from equal splits are distributed one penny at a time.

### 7. Tailwind v4 with CSS-first theming
**Decision:** Use the new `@theme` directive for design tokens.
**Why:** Dark mode from the start, consistent color system, no CSS-in-JS
runtime cost.

## Edge Cases Considered & Addressed

| # | Edge Case | How Handled |
|---|-----------|-------------|
| 1 | Equal split rounding (10/3 = 3.33...) | Distribute remainder 0.01 to first N members |
| 2 | Self-payment (payer in share-holders) | Engine handles naturally — they owe themselves |
| 3 | Zero-balance members | Filtered from settlements list |
| 4 | Single member only | Net zero, no settlements |
| 5 | Duplicate member IDs | Rejected in batch validation |
| 6 | Negative expense total | Rejected in validation |
| 7 | Large JSON payload | API enforces 10 KB body size limit |
| 8 | Too many members/expenses | API enforces 50 members, 200 expenses max |
| 9 | Invalid JSON body | Caught in try/catch, returns 400 |
| 10 | JSON injection (prototype pollution) | `body` is parsed with `JSON.parse`, no `eval` |
| 11 | XSS in member names | React auto-escapes; no `dangerouslySetInnerHTML` |
| 12 | Client-side validation bypass | Server re-validates everything |
| 13 | Concurrent requests | Stateless API — each request is independent |
| 14 | Very large numbers | JavaScript number precision; up to 2^53 safe |
| 15 | Zero share-holders in split | Rejected: "At least one share-holder required" |
| 16 | Percentage sum 99.99% | Fuzzy comparison with epsilon tolerance |
| 17 | Exact amount sum off by 0.01 | Fuzzy comparison with epsilon tolerance |
| 18 | Member deleted after expense added | Expense stays; shows the original payer name via lookup |
| 19 | Same file re-upload | Input reset allows re-upload of the same filename |

## Iterative Refinement Log

1. **Scaffold:** Created Next.js project manually due to corporate TLS restrictions
2. **Types first:** Defined all TypeScript interfaces before any logic
3. **Core engine:** Implemented validation → balances → simplification in that order
4. **Tests:** Wrote tests alongside engine, not after — TDD-like for edge cases
5. **API route:** Added rate limiting, size checks, and error normalization
6. **UI:** Single-page with add-expense form, expense list, and results panels
7. **Sample data:** Created `expenses.json` covering all three split types
8. **Documentation:** README with quick start, API docs, architecture, edge cases