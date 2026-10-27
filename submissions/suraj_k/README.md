# Splitwise-Lite: Team Outing Expense Settler

A production-grade expense splitting engine — compute net balances and minimize settlement transactions. Zero external dependencies. 119 tests. All edge cases covered.

## Quick Start

```bash
# Process a single JSON file
python run.py input.json

# Process a batch directory
python run.py batch/fixtures/

# Pipe JSON from stdin
cat data.json | python run.py --stdin

# Output to file
python run.py input.json --output result.json

# Balances only (no settlements)
python run.py input.json --balances-only

# Compact (no indentation)
python run.py input.json --compact
```

## Features

| Category | Feature | Implementation |
|----------|---------|----------------|
| **M1: Splits** | Equal, Exact, Percentage | `Split` ABC with cached shares — residue absorbed by last participant |
| **M2: Balances** | Net paid/owed per member | `BalanceCalculator.compute()` — pure function, O(n) |
| **M3: Settlements** | Minimum transactions | Greedy max-heap — O(n log n), handles cyclical debts |
| **M4: Batch** | Single & batch JSON processing | `JSONProcessor` — collects all errors, no fail-on-first |
| **M5: Validation** | Strict input rules | Percentages=100, exact sums=total, payer exists, amounts>0 |
| **Edge 1** | Fractional paisa (₹100÷3) | Residue absorbed by last participant; cached shares |
| **Edge 2** | Decimal precision | `Decimal` everywhere, `MONEY_CONTEXT` (prec=28), sub-paisa guard, NaN/Inf guard |
| **Edge 3** | Cyclical debts | Net-balance approach — A→B→C→A yields 0 transactions |
| **Edge 4** | Self-payment, single-member | Legal from the ground up — net=0, no settlements |
| **Edge 5** | Inactive members | Soft-delete via `Member.active` flag — preserves history |

### Unlisted Edge Cases Covered

- Duplicate participants in a split → rejected
- Negative exact amounts → rejected
- Negative percentages → rejected
- NaN / Infinity in JSON → rejected
- Control characters in member names → rejected
- Member name length > 100 chars → rejected
- Description length > 500 chars → rejected
- File size > 50 MiB → rejected before parse
- Group member count > 10,000 → rejected
- Expense count > 100,000 → rejected

## Architecture

```
src/
├── models/              # Domain value objects (immutable)
│   ├── member.py        # Member with soft-delete (active flag)
│   ├── split.py         # Split ABC + Equal/Exact/Percentage + validate_amount()
│   ├── expense.py       # Expense with payer-in-split enforcement
│   └── transaction.py   # BalanceSnapshot + Transaction (frozen dataclasses)
├── services/            # Business logic (pure functions where possible)
│   ├── group_manager.py # Aggregate root with member lifecycle
│   ├── balance.py       # BalanceCalculator
│   ├── settlement.py    # SettlementEngine (greedy max-heap)
│   └── json_processor.py# JSONProcessor + security guards
├── errors.py            # 7-class exception hierarchy
└── cli.py               # argparse-based CLI
tests/
├── fixtures/            # 7 JSON samples (4 valid, 3 invalid)
├── test_split.py        # Split computation + inactive-member rejection
├── test_validation.py   # Amount validation + duplicate/negative guards + NaN
├── test_balance.py      # Net balance computation + residue + self-payment
├── test_expense.py      # Expense value object
├── test_group_manager.py# Member lifecycle + self-payment + inactive
├── test_settlement.py   # Settlement engine + cyclical + 1000-member stress
├── test_json_processor.py# File/batch/stdin + security edge cases
└── test_integration.py  # End-to-end: all 5 edge cases
```

## Input Format

```json
{
  "group": {
    "name": "Team Outing 2026",
    "members": ["Alice", "Bob", "Charlie", "Diana"]
  },
  "expenses": [
    {
      "description": "Dinner",
      "payer": "Alice",
      "amount": 120.00,
      "split": {
        "type": "equal",
        "participants": ["Alice", "Bob", "Charlie", "Diana"]
      }
    },
    {
      "description": "Taxi",
      "payer": "Bob",
      "amount": 45.00,
      "split": {
        "type": "exact",
        "participants": ["Alice", "Bob", "Charlie"],
        "amounts": { "Alice": 15.00, "Bob": 15.00, "Charlie": 15.00 }
      }
    },
    {
      "description": "Hotel Suite",
      "payer": "Diana",
      "amount": 400.00,
      "split": {
        "type": "percentage",
        "participants": ["Alice", "Diana"],
        "percentages": { "Alice": 40, "Diana": 60 }
      }
    }
  ]
}
```

## Run Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
# 119 tests, 0 failures
```

## Design Decisions

| Choice | Rationale |
|--------|-----------|
| `Decimal` everywhere | `float` can't represent ₹0.10 exactly — correctness bug for money |
| Strategy pattern for splits | Open/closed — add a split type by subclassing, zero changes to Expense |
| Cached share computation | `share_for(m)` ≡ `shares()[m]` — eliminates the two-values-for-one-member bug |
| Greedy max-heap settlement | O(n log n), produces minimum transactions in practice |
| No external dependencies | stdlib only — `decimal`, `heapq`, `json`, `unittest`, `argparse` |
| Immutable value objects | `Expense`, `Split`, `Transaction` constructed once, never mutated |
| Custom exception hierarchy | Every error catchable by type, not string matching |
| Batch errors collected | Process all files, report every violation — fail-on-first loses signal |
| Soft-delete (tombstone) | `Member.active=False` preserves referential integrity in historical expenses |
| Centralised amount guard | `validate_amount()` shared by Expense.__init__ and JSONProcessor |

## Project Files

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Full design blueprint with pattern registry, algorithm, and evolution log |
| `PROMPTS.md` | AI collaboration log — prompt methodology, decisions, and traceability matrix |
| `.gitignore` | Python-standard patterns to keep the repo clean |