# Expense Splitter — Splitwise-lite

A team-outing expense settler. Add expenses with three split types, see
net balances, and get a simplified debt settlement plan.

## Quick start

```bash
# 1. Install (requires Python 3.9+)
cd submissions/rawat_anil
pip install -r requirements.txt        # pytest only — zero runtime deps

# 2. Run on the sample data
python -m expense_splitter sample_expenses.json

# 3. Run on batch data (multiple groups)
python -m expense_splitter sample_batch.json

# 4. JSON output (machine-readable)
python -m expense_splitter sample_expenses.json --json
```

## Input format

A JSON file with a single group, or an array of groups (batch mode).

```json
{
  "group": "Goa Trip 2026",
  "members": ["Anil", "Priya", "Raj", "Simran", "Vikram"],
  "expenses": [
    {
      "description": "Flight tickets",
      "total": 45000,
      "paid_by": "Anil",
      "split_type": "equal",
      "members": ["Anil", "Priya", "Raj", "Simran", "Vikram"]
    },
    {
      "description": "Dinner (exact shares)",
      "total": 6500,
      "paid_by": "Raj",
      "split_type": "exact",
      "members": ["Anil", "Priya", "Raj", "Simran"],
      "amounts": [1800, 1200, 2000, 1500]
    },
    {
      "description": "Scooter rentals",
      "total": 5000,
      "paid_by": "Vikram",
      "split_type": "percentage",
      "members": ["Anil", "Priya", "Raj", "Simran", "Vikram"],
      "amounts": [10, 10, 30, 30, 20]
    }
  ]
}
```

### Split types

| Type         | `amounts` field                | Validation                                     |
| ------------ | ------------------------------ | ---------------------------------------------- |
| `equal`      | Not needed                     | —                                              |
| `exact`      | Exact ₹ amounts per member     | Must sum to `total`, same count as `members`   |
| `percentage` | Percentages (0–100) per member | Must sum to 100%, same count as `members`      |

## Output

### Pretty-print (default)

```
══════════════════════════════════════════
  Group: Goa Trip 2026
  Members: Anil, Priya, Raj, Simran, Vikram
  Expenses processed: 6
══════════════════════════════════════════

  📊 NET BALANCES
  ──────────────────────────────────────────
  Member               Paid       Owed        Net
  ──────────────────────────────────────────
  Anil                54000    17900.00    +36100.00
  ...

  💸 SIMPLIFIED SETTLEMENTS
  ──────────────────────────────────────────
  Priya  ──₹4,400.00──▶  Anil
  Raj  ──₹6,300.00──▶  Anil
  ...
```

### JSON (`--json`)

```json
[
  {
    "group": "Goa Trip 2026",
    "members": ["Anil", "Priya", "Raj", "Simran", "Vikram"],
    "expenses_processed": 6,
    "errors": [],
    "balances": {
      "Anil": {"paid": 54000.0, "owed": 17900.0, "net": 36100.0}
    },
    "settlements": [
      {"from": "Priya", "to": "Anil", "amount": 4400.0}
    ]
  }
]
```

## Architecture

```
expense_splitter/
├── __init__.py        # Package metadata
├── __main__.py        # Enables `python -m expense_splitter`
├── models.py          # Dataclasses: Expense, Balance, Settlement, SplitResult
├── validator.py       # Input validation with clear error messages
├── engine.py          # Balance computation + greedy debt simplification
└── cli.py             # argparse CLI, JSON loading, pretty printing

tests/
├── test_expense_splitter.py  # Unit tests: 25+ cases covering M1–M5 and edges
└── test_integration.py       # End-to-end CLI tests on sample files
```

## Debt simplification algorithm

Greedy settlement: repeatedly match the member who owes the most with the
member who is owed the most, settling the smaller of the two magnitudes.
This produces a settlement list with at most `n-1` entries for `n` members
(and is optimal for most real-world groups).

## Running tests

```bash
cd submissions/rawat_anil
python -m pytest tests/ -v
```

## Design decisions

- **Zero runtime dependencies** — only stdlib (`argparse`, `json`, `dataclasses`).
  `pytest` is the sole dev dependency.
- **Rounding-safe** — all monetary values are explicitly rounded to 2 decimal
  places after every operation. Rounding differences from equal/percentage
  splits are absorbed by the last member's share.
- **Validation-first** — structural checks run before any computation.
  Invalid expenses are collected and reported together; valid expenses still
  process to completion.
- **Batch support** — a single JSON array can hold multiple groups; each
  processes independently, and any error exits non-zero.