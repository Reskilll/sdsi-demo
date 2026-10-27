# PROMPTS.md — AI Collaboration Record

This document records the actual prompts used and steps taken during development of the ExpenseSplitter application for SDSI Digithon 2026 (PS1).

---

## Initial Prompt

The full problem statement from the hackathon brief was provided as the initial prompt. It specified:
- PS1: Expense Splitter with Debt Simplification
- Tech stack: React + Vite, JavaScript, Modern CSS, localStorage, Vitest
- Core requirements M1–M5, UI, testing, documentation, git hygiene
- A working method of Inspect → Plan → Implement → Test → Polish → Document → Verify

## Project Scaffolding

**Action**: Used `npm create vite@latest . -- --template react` inside `submissions/vaas778/`.

**Outcome**: Generated a Vite + React scaffold. Modified `package.json` to add Vitest dependency and test scripts, added test configuration to `vite.config.js`.

---

## Logic Module Implementation

**Prompt**: "Implement the core business logic as pure functions in src/logic/"

Modules implemented:

### splitExpense.js
- `calculateShares()` dispatches to equal, exact, or percentage split functions
- Equal split: deterministic remainder distribution (alphabetical order)
- Exact split: validates sum equality
- Percentage split: largest-remainder method for rounding

### validateExpense.js
- Validates description, amount, payer membership, participant membership, duplicates
- Split-type-specific validation for exact amounts and percentages
- Date validation
- Duplicate ID checking

### calculateBalances.js
- Iterates all expenses, credits payer, debits participants
- Returns { memberId, paid, owed, balance } for every member

### simplifyDebts.js
- Greedy algorithm: sort creditors and debtors by amount, match largest with largest
- `verifySettlements()` to confirm balance resolution

### importExpenses.js
- JSON parsing with error handling
- Member and expense validation
- Atomic batch import (reject all if any invalid)

---

## Currency Utility

**Prompt**: "Create utility functions for paise/rupee conversion with Indian formatting"

Implemented in `src/utils/currency.js`:
- `rupeesToPaise()` with Math.round()
- `paiseToRupees()` using toLocaleString('en-IN')
- `formatSignedBalance()` for +₹/-₹ display
- `paiseToDecimal()` for debug output

---

## React Components and Hook

**Prompt**: "Build the React UI as a polished SaaS-style dashboard"

Implemented:
- `useExpenseData` hook: Central state with localStorage persistence, derived balances and settlements via useMemo
- `Dashboard.jsx`: SummaryCards, MemberBalances, SettlementList, ExpenseList, MemberManager, JsonImport
- `ExpenseForm.jsx`: Dynamic form with live share preview, inline validation
- `App.jsx`: View routing (dashboard / add-expense / members / import)

---

## Test Suite

**Prompt**: "Write comprehensive Vitest tests covering split calculations, validation, balances, debt simplification, and import"

### Tests written: 77 total across 6 files

- **splitExpense.test.js** (16 tests): Equal split with remainder, exact split validation, percentage rounding, edge cases
- **validateExpense.test.js** (17 tests): Field validation, member checks, split-type-specific rules, date handling
- **calculateBalances.test.js** (6 tests): Single/multiple expenses, payer exclusion, zero-balance members, zero-sum verification
- **simplifyDebts.test.js** (10 tests): Simple/multiple creditors, determinism, self-payment prevention, settlement verification
- **importExpenses.test.js** (17 tests): Valid/invalid JSON, batch atomicity, member validation, duplicate handling
- **currency.test.js** (11 tests): Conversion accuracy, formatting, edge cases

### Test execution: All 77 tests passed on first run.

---

## Build Fix

**Bug**: Initial build failed with `MISSING_EXPORT` error — Dashboard.jsx used `export default function` but App.jsx imported via named imports.

**Fix**: Changed all Dashboard component exports from `export default function` to `export function`.

**Outcome**: Build succeeds, producing `dist/` with index.html, CSS, and JS bundle (~75 KB gzipped).

---

## UI Polish

**Prompt**: "Polish the UI with CSS custom properties, responsive grid, hover states, and accessible contrast"

Applied:
- CSS custom properties for consistent theming (indigo accent)
- Responsive layouts: 4-col → 2-col → 1-col summary cards
- Professional card styling with subtle borders and rounded corners
- Color-coded balances (green/red)
- Empty states for all sections
- Focus ring with box-shadow
- Chip-style participant selector
- Tab-style split type switcher

---

## Manual Verification

Items verified manually:
- [x] App starts with `npm run dev`
- [x] Add members, add expenses with all three split types
- [x] Balances update immediately on add/delete
- [x] Debt simplification produces valid settlements
- [x] JSON import with sample data works
- [x] Invalid JSON import shows error, doesn't corrupt state
- [x] Data persists across page refresh (localStorage)
- [x] Responsive layout on narrow viewport
- [x] All 77 tests pass with `npm test`
- [x] Production build succeeds with `npm run build`

---

## Summary

The development was efficient. The key architecture decision — separating pure business logic from React components — allowed comprehensive testing without DOM dependencies. The greedy debt simplification algorithm was chosen for simplicity and determinism over theoretical optimality, which is documented honestly in the README.

No significant bugs were discovered during review. The only build issue was the named export mismatch which was immediately caught and fixed.