# Expense Splitter — Team Outing Settler

A single-page browser app that settles group expenses and simplifies debts into the
minimum number of "A pays B ₹X" payments — like Splitwise, but simpler.

## Quick start

Open **`expense-splitter.html`** in any modern browser. No server, no install.

## Features

| # | Feature | How |
|---|---|---|
| M1 | Three split types | **Equal** (all members split equally), **Exact Amounts** (per-person ₹), **Percentage** (per-person % that must sum to 100) |
| M2 | Net balances | Each member's net position — "gets back ₹X" (green) or "owes ₹X" (red) |
| M3 | Debt simplification | Greedy algorithm matches largest creditors with largest debtors → minimal "A pays B ₹X" settlement list |
| M4 | JSON import/export | Import single `{...}`, array `[{...}]`, or `{members, expenses}` export format. Export downloads portable `.json`. |
| M5 | Input validation | Percentages must sum to 100%, exact shares must sum to the total, payer must be a group member, no empty shares |

## Data persistence

- **localStorage** auto-saves on every change (add/remove member, add/remove expense, import).
- Data survives page refresh.
- **Export** downloads a portable `expenses.json` for backup or sharing.
- **Reset All** clears localStorage.

## Sample data

Drag **`sample-expenses.json`** onto the import area or paste its contents:

```json
[
  { "description": "Dinner at Punjabi Dhaba", "amount": 2400, "paidBy": "Alice", "split": "equal" },
  { "description": "Petrol for road trip",    "amount": 900,  "paidBy": "Bob", "split": "exact", "shares": { "Alice": 300, "Charlie": 600 } },
  { "description": "Movie tickets",           "amount": 1200, "paidBy": "Charlie", "split": "percent", "shares": { "Alice": 50, "Bob": 30, "Charlie": 20 } },
  { "description": "Snacks & drinks",         "amount": 400,  "paidBy": "Alice", "split": "equal" },
  { "description": "Parking",                 "amount": 200,  "paidBy": "Bob", "split": "exact", "shares": { "Alice": 100, "Bob": 50, "Charlie": 50 } }
]
```

## How the simplification works

The algorithm:
1. Computes each member's net balance (total paid — total owed).
2. Separates into **creditors** (positive net, owed money) and **debtors** (negative net, owes money).
3. Sorts both lists largest-first.
4. Greedily matches: largest debtor pays largest creditor until one is settled, then moves to the next.
5. This produces the minimum (or very near minimum) number of transactions — the classic Splitwise algorithm.

## Architecture

Single self-contained HTML file — zero dependencies:
- **State:** `members[]` and `expenses[]` arrays
- **Persistence:** `localStorage` under key `expense_splitter_data`
- **Validation:** `validateExpense()` — split-type-aware checks with floating-point epsilon tolerance
- **Simplification:** `simplifyDebts()` — greedy max-first creditor/debtor matching
- **Security:** All user-supplied strings HTML-attribute-escaped before `innerHTML` insertion