# ExpenseSplitter

A lightweight expense-splitting application — a simplified Splitwise clone — built for the SDSI Digithon 2026 hackathon (PS1).

## Features

- **Three split types**: Equal, Exact Amounts, and Percentage splits
- **Net balance calculation**: Aggregates across all expenses with precise paise-level arithmetic
- **Debt simplification**: Greedy algorithm minimizes the number of settlement transactions
- **Member management**: Add and remove group members with safety checks
- **JSON import**: Bulk-import members and expenses with atomic validation
- **localStorage persistence**: Data survives page refreshes; no backend required
- **Responsive UI**: Works on desktop, tablet, and mobile

## Technology Stack

- **React 19** with Vite
- **JavaScript** (ESM)
- **Modern CSS** (CSS custom properties, grid, flexbox)
- **localStorage** for persistence
- **Vitest** for unit testing
- No backend, no database, no external API calls

## Prerequisites

- Node.js 18+
- npm 9+

## Installation

```bash
cd submissions/vaas778
npm install
```

## Running the Application

```bash
npm run dev
```

Opens at `http://localhost:5173` by default.

## Running Tests

```bash
npm test
```

Or in watch mode:

```bash
npm run test:watch
```

## JSON Import Schema

Import members and expenses from a JSON file:

```json
{
  "members": [
    { "id": "aman", "name": "Aman" },
    { "id": "rahul", "name": "Rahul" }
  ],
  "expenses": [
    {
      "id": "exp-1",
      "description": "Dinner",
      "amount": 1500,
      "paidBy": "aman",
      "splitType": "equal",
      "participants": ["aman", "rahul", "priya"],
      "date": "2026-10-27"
    },
    {
      "id": "exp-2",
      "description": "Groceries",
      "amount": 850,
      "paidBy": "priya",
      "splitType": "exact",
      "participants": ["aman", "priya", "neha"],
      "exactAmounts": { "aman": 300, "priya": 250, "neha": 300 },
      "date": "2026-10-27"
    },
    {
      "id": "exp-3",
      "description": "Cab fare",
      "amount": 500,
      "paidBy": "neha",
      "splitType": "percentage",
      "participants": ["aman", "rahul", "neha"],
      "percentages": { "aman": 40, "rahul": 40, "neha": 20 },
      "date": "2026-10-27"
    }
  ]
}
```

### Schema Rules

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `members[].id` | string | Yes | Unique identifier |
| `members[].name` | string | Yes | Display name |
| `expenses[].id` | string | No | Auto-generated if omitted |
| `expenses[].description` | string | Yes | Must not be empty |
| `expenses[].amount` | number | Yes | In rupees, must be positive |
| `expenses[].paidBy` | string | Yes | Must match an existing or imported member ID |
| `expenses[].splitType` | string | Yes | `"equal"`, `"exact"`, or `"percentage"` |
| `expenses[].participants` | string[] | Yes | Valid member IDs, no duplicates |
| `expenses[].exactAmounts` | object | For exact | Maps member ID to rupee amount; must sum to `amount` |
| `expenses[].percentages` | object | For percentage | Maps member ID to percentage; must sum to 100 |
| `expenses[].date` | string | No | ISO 8601 date (YYYY-MM-DD) |

**Import behavior**:
- Unknown top-level and expense keys are **ignored** (not rejected).
- Batch imports are **atomic**: if any expense is invalid, nothing is imported.
- Duplicate expense IDs are rejected. Duplicate member IDs (matching existing members) are skipped gracefully.
- Malformed JSON is rejected with an error message.

A sample file is included at `sample-data/expenses.json`.

## Split Methods

### Equal Split

The total amount is divided equally among all selected participants. Any remainder (in paise) is distributed deterministically — one paisa each to the first participants in alphabetical order by ID.

### Exact Amount Split

Each participant's exact share in rupees is specified. The sum of all shares must exactly equal the total expense amount. Invalid totals are rejected.

### Percentage Split

Each participant's percentage of the total is specified. Percentages must sum to 100% (with a tolerance of 0.001%). Shares are calculated using the largest-remainder method to ensure no money is created or lost.

## Balance Calculation

For each member:

```
Net Balance = Total Amount Paid − Total Amount Owed (through expense shares)
```

- **Positive balance**: The member is owed money (creditor).
- **Negative balance**: The member owes money (debtor).
- **Zero balance**: The member is settled.

All calculations use integer paise internally. The sum of all net balances always equals zero.

## Debt Simplification Algorithm

We use a **greedy algorithm** that:

1. Separates members into creditors (positive balance) and debtors (negative balance).
2. Sorts both groups by balance amount descending (tie-breaking by member ID for determinism).
3. At each step, settles between the largest creditor and largest debtor for the minimum of their absolute amounts.
4. Repeats until all balances are settled.

**Properties**:
- Produces a near-minimal number of transactions (2-approximation of optimal).
- Deterministic for identical inputs.
- Never generates self-payments, zero-value settlements, or over-settlement.
- Verified: applying settlements always results in zero balances for all members.

## Currency Precision and Rounding Policy

- All internal currency values are **integer paise** (1 paisa = 1/100 ₹).
- Conversion from rupees (float) to paise uses `Math.round()`.
- Equal split remainder: extra paise distributed to alphabetically-first participants.
- Percentage split remainder: largest-remainder method (sort by fractional paise descending).
- Exact split: no rounding needed; values specified directly in rupees.
- Display formatting uses `toLocaleString('en-IN')` with two decimal places.

## Design Decisions and Limitations

1. **Greedy simplification**: Does not guarantee the absolute minimum number of transactions for all cases, but is fast, deterministic, and correct. A minimum-transaction algorithm (max-flow/min-cut formulation) could be added for smaller groups.

2. **Atomic imports only**: Batch imports are all-or-nothing. Partial imports are not supported to prevent data inconsistency.

3. **Member removal guard**: Members referenced in any expense cannot be removed. Delete their expenses first.

4. **No settlement tracking**: The app suggests settlements but does not track which settlements have been "paid." This is by design — it's a calculator, not a payment system.

5. **localStorage**: Data persists in the browser. Clearing browser data or switching browsers loses data. No export feature beyond the import/export round-trip via JSON.

6. **Unknown JSON fields are ignored**: This is friendlier for interoperability while still rejecting invalid required fields.

7. **Payer optional in participants**: The payer can be excluded from the split (e.g., treating someone). This is intentionally allowed.

## Project Structure

```
vaas778/
  src/
    components/
      Dashboard.jsx / .css     — All dashboard components
      ExpenseForm.jsx / .css   — Add-expense form
    logic/
      splitExpense.js          — Split calculations (equal, exact, percentage)
      validateExpense.js       — Input validation
      calculateBalances.js     — Net balance computation
      simplifyDebts.js         — Greedy debt simplification
      importExpenses.js        — JSON parse + validate + build
    utils/
      currency.js              — Paise/rupee conversion
      helpers.js               — ID generation, deep clone
    hooks/
      useExpenseData.js        — Central state hook
    App.jsx                    — Root component
    main.jsx                   — Entry point
  tests/
    splitExpense.test.js
    validateExpense.test.js
    calculateBalances.test.js
    simplifyDebts.test.js
    importExpenses.test.js
    currency.test.js
  sample-data/
    expenses.json              — Sample import file
  README.md                    — This file
  PROMPTS.md                   — AI collaboration record
```