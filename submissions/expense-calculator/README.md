# SplitSage — Expense Splitter with Debt Simplification

A team-outing expense settler (Splitwise-lite) built with Next.js 15 and
TypeScript. Adds expenses with three split types, shows net balances, and
simplifies debts into the minimum number of "A pays B ₹X" settlements.

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev
# → http://localhost:3000

# Run tests
npm test

# Production build
npm run build && npm start
```

## Features

| Feature | Description |
|---------|-------------|
| **Three split types** | Equal, Exact amounts, Percentage |
| **Net balance view** | Per-member: what they paid, what they owe, net position |
| **Debt simplification** | Greedy minimum-cash-flow algorithm → fewest settlements |
| **JSON batch upload** | Upload `expenses.json` to bulk-load members + expenses |
| **Input validation** | Percentages must sum to 100%, exact amounts to total, payer must be a member |
| **Live preview** | See results update instantly in the browser |

## API

### `POST /api/expenses`

```json
{
  "members": [
    { "id": "alice", "name": "Alice" },
    { "id": "bob", "name": "Bob" }
  ],
  "expenses": [
    {
      "description": "Dinner",
      "total": 2500,
      "paidBy": "alice",
      "split": {
        "type": "equal",
        "shareHolderIds": ["alice", "bob"]
      }
    }
  ]
}
```

Returns:
```json
{
  "balances": [
    { "memberId": "alice", "name": "Alice", "paid": 2500, "owed": 1250, "net": 1250 },
    { "memberId": "bob", "name": "Bob", "paid": 0, "owed": 1250, "net": -1250 }
  ],
  "settlements": [
    { "from": "bob", "to": "alice", "amount": 1250 }
  ],
  "totalExpenses": 2500,
  "expenseCount": 1
}
```

### `GET /api/expenses`

Returns API documentation.

## Sample Data

```bash
# In the app, click "Upload JSON" and select:
sample-data/expenses.json
```

This file contains 4 members and 4 expenses (equal, exact, percentage, equal)
that exercise all three split types.

## Architecture

```
src/
  app/
    page.tsx          → Single-page UI (members, expenses, results)
    layout.tsx        → Root layout
    globals.css       → Tailwind + theme
    api/expenses/
      route.ts        → POST / GET handlers
  lib/
    engine.ts         → Core logic (validation, balances, debt simplification)
    engine.test.ts    → Comprehensive test suite
    types.ts          → TypeScript type definitions
sample-data/
  expenses.json       → Sample batch input
```

### Debt Simplification Algorithm

1. Compute net balance for each member (paid — owed)
2. Separate into creditors (positive) and debtors (negative)
3. While both lists non-empty:
   - Match largest creditor with largest debtor
   - Settle the smaller of the two amounts
   - Reduce balances, remove zero
4. Produces ≤ ceiling(n - k) settlements (theoretical minimum)

### Edge Cases Covered

- Floating-point drift (all amounts rounded to 2 decimal places)
- Zero-balance members (excluded from settlements)
- Single-member groups (self-payment → net zero, no settlements)
- Rounding remainders in equal splits (distributed penny by penny)
- Negative/zero totals
- Invalid members in splits
- Duplicate member IDs
- Empty input
- Percentage not summing to 100
- Exact amounts not summing to total
- Very large inputs (rate-limited by API)

## Sample Scenarios

### Scenario 1: Simple dinner split
Alice pays ₹4000 for dinner for 4 people. Equal split.
→ Each owes ₹1000. Alice is owed ₹3000 from Bob, Charlie, Diana.

### Scenario 2: Mixed split types
Bob pays ₹600 taxi (exact: Alice ₹200, Bob ₹100, Charlie ₹300).
Charlie pays ₹3000 concert (percentage: Alice 40%, Bob 30%, Charlie 30%).
→ Engine computes net balances and produces minimal settlements.

## Tech Stack

- **Next.js 15** (App Router) with React 19
- **TypeScript** (strict mode)
- **Tailwind CSS v4** + PostCSS
- **Node.js Test Runner** (native `node --test`)
- **Zero external test dependencies**

## License

MIT