# PROMPTS.md — Problem breakdown and prompt refinement log

## Problem breakdown

**Goal**: Expense Splitter with Debt Simplification (Splitwise-lite)

**Must-have (M1–M5):**
1. Add expenses with split types: equal, exact amounts, percentage
2. Show each member's net balance
3. Simplify debts into minimum "A pays B ₹X" settlements
4. Process JSON expense files (batch)
5. Validate inputs: % sum=100, exact sum=total, payer is member

**Edge cases (E1–E3):**
1. Single-member group
2. Zero/rounding in percentage splits (e.g., 33.33%+33.33%+33.34%)
3. Debt cycles (A→B→C→A) → optimal simplification

**Stretch** (post-MVP):
- Expense history / undo / formatted report

## Prompt 1: Initial codegen

Requested a complete Python solution with core/CLI/tests structure under `submissions/Stoicall/`.

**AI suggestion (accepted):** Use `Decimal` for all monetary calculations to avoid float drift.  
**AI suggestion (accepted):** Greedy netting algorithm (largest debtor→largest creditor) for near-minimum transactions.

## Prompt 2: Rounding approach

**Issue found during review:** `ROUND_HALF_UP` was imported as the wrong constant spelling, and the `_compute_shares` remainder distribution for equal splits used a flat `ROUND_HALF_UP` base per person that could over-allocate pennies.

**Correction:** Replaced the simple rounding with a remainder-distribution approach:
- For equal splits: compute base = rounded(avg), then add/subtract 0.01 from first-K members to absorb the remainder.
- For percentage splits: sum the individually-rounded shares, adjust the largest share by the residual paise.

## Prompt 3: Edge case tests

**Testing single-member group:** My first test expected `ExpenseError` when a single member was both payer and in the split group. **I corrected this** — a single member paying for themselves is valid (net = 0). Changed test to assert zero balance instead.

## Prompt 4: CLI entry point

Added `cli.py` with `process` command to read JSON files. The CLI is thin — it parses args, delegates to `ExpenseSplitter`, prints the report. No business logic lives in the CLI.

## Review log

| Refinement | Before | After |
|---|---|---|
| Rounding equal split | Flat rounded-per-person | Remainder-distribution to first members |
| Import typo | `ROUND_DOWN` imported but `ROUND_HALF_UP` used | Consistent `ROUND_HALF_UP` |
| Test logic error | Expected error on valid single-member case | Fixed to assert net=0 |
| Field rendering | `⚖ ₹0` for balances | `+₹0.00` / `-₹0.00` with sign and 2 decimals |