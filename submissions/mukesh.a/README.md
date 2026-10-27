# Expense Splitter with Debt Simplification

A lightweight, zero-dependency Python tool for splitting group expenses and simplifying debts — a Splitwise-lite for team outings.

## Features

- **Three split types**: equal, exact amounts, and percentage-based
- **Net balance computation**: who owes whom, netted across all expenses
- **Debt simplification**: reduces payments to the minimum (or near-minimum) number of transactions using a greedy max-creditor↔max-debtor matching algorithm
- **Robust validation**: checks percentages sum to 100, exact amounts match totals, payer is a group member, and more
- **Batch processing**: handle multiple groups from a single input file
- **CLI & library**: use as a command-line tool or import the Python API

## Quick Start

```bash
# No install needed — pure Python standard library only
cd submissions/mukesh.a

# Run with built-in sample data
python run.py --sample

# Run from a JSON file
python run.py samples/expenses.json

# Run a batch file (multiple groups)
python run.py --batch samples/batch.json
```

## Input Format

### Single Group

```json
{
  "name": "Team Outing",
  "members": ["Alice", "Bob", "Charlie"],
  "expenses": [
    {
      "title": "Dinner",
      "total_amount": 6000,
      "paid_by": "Alice",
      "split_type": "equal",
      "members": ["Alice", "Bob", "Charlie"]
    }
  ]
}
```

### Split Types

| Type | `split_type` | Extra fields |
|------|-------------|--------------|
| **Equal** | `"equal"` | `members` — everyone pays an equal share |
| **Exact** | `"exact"` | `shares` — `{member: amount, ...}` must sum to `total_amount` |
| **Percentage** | `"percentage"` | `shares` — `{member: pct, ...}` must sum to 100 |

## Output Format

```json
{
  "group": "Team Outing",
  "members": ["Alice", "Bob", "Charlie"],
  "expenses": [
    {
      "title": "Dinner",
      "total_amount": 6000.0,
      "paid_by": "Alice",
      "split_type": "equal",
      "shares": { "Alice": 2000.0, "Bob": 2000.0, "Charlie": 2000.0 }
    }
  ],
  "balances": {
    "Alice": 4000.0,
    "Bob": -2000.0,
    "Charlie": -2000.0
  },
  "settlements": [
    { "from": "Bob", "to": "Alice", "amount": 2000.0 },
    { "from": "Charlie", "to": "Alice", "amount": 2000.0 }
  ]
}
```

## Running Tests

```bash
# Run all tests
python -m pytest test_expense_splitter.py -v

# Or with unittest directly
python test_expense_splitter.py
```

## API Usage

```python
from expense_splitter import process_group, process_batch, ValidationError

# Single group
result = process_group(
    group_name="Trip",
    members=["A", "B", "C"],
    expenses_data=[
        {
            "title": "Hotel",
            "total_amount": 300,
            "paid_by": "A",
            "split_type": "equal",
            "members": ["A", "B", "C"],
        }
    ],
)
print(result["balances"])
print(result["settlements"])
```

## Project Structure

```
submissions/mukesh.a/
├── expense_splitter.py   # Core module: models, validation, logic
├── run.py                # CLI entry point
├── test_expense_splitter.py  # Comprehensive test suite
├── samples/
│   └── expenses.json     # Sample expense data
├── README.md             # This file
└── PROMPTS.md            # AI collaboration notes
```