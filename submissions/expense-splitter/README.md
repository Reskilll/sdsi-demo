# Expense Splitter — Splitwise-lite

A Python CLI + library for splitting team-outing expenses and settling
debts with the fewest possible transactions.

## Features

| # | Criterion | Status |
|---|-----------|--------|
| M1 | Equal, exact, and percentage splits | ✅ |
| M2 | Net balance per member | ✅ |
| M3 | Simplified settlement list ("A pays B ₹X") | ✅ |
| M4 | JSON file input (single or batch) | ✅ |
| M5 | Input validation (sums, payer-in-group) | ✅ |

## Project structure

```
expense-splitter/
├── expense_splitter/
│   ├── __init__.py       # package metadata
│   ├── models.py         # Expense, Settlement, SplitType
│   ├── validation.py     # input validation (M5)
│   ├── balance.py        # net balance computation (M2)
│   ├── simplify.py       # debt simplification (M3)
│   ├── processor.py      # orchestration pipeline
│   └── cli.py            # command-line entry point
├── tests/
│   └── test_all.py       # comprehensive pytest suite
├── sample_expenses.json  # demo data
├── PROMPTS.md            # AI collaboration log
├── README.md             # this file
├── pyproject.toml        # build config
└── .gitignore
```

## Quick start

```bash
# Install (editable)
pip install -e .

# Run with sample data
expense-splitter sample_expenses.json

# Run with multiple files
expense-splitter jan.json feb.json

# Machine-readable output
expense-splitter --json-out sample_expenses.json

# Run tests
pytest tests/ -v
```

## Input format

A JSON file with a single expense object **or** an array of expense
objects:

```json
[
  {
    "description": "Team dinner at Spice Garden",
    "paid_by": "Alice",
    "total_amount": 4500,
    "split_type": "equal",
    "participants": ["Alice", "Bob", "Charlie"]
  },
  {
    "description": "Movie tickets",
    "paid_by": "Charlie",
    "total_amount": 1200,
    "split_type": "exact",
    "participants": ["Alice", "Bob", "Charlie"],
    "splits": {"Alice": 500, "Bob": 400, "Charlie": 300}
  },
  {
    "description": "Drinks at rooftop bar",
    "paid_by": "Alice",
    "total_amount": 2000,
    "split_type": "percentage",
    "participants": ["Alice", "Bob", "Charlie"],
    "splits": {"Alice": 50, "Bob": 30, "Charlie": 20}
  }
]
```

### Split types

| Type | `splits` dict | Constraint |
|------|---------------|------------|
| `equal` | **No** splits key | Total ÷ N |
| `exact` | Member → ₹amount | Sum must equal `total_amount` |
| `percentage` | Member → % | Sum must equal 100 |

## How it works

1. **Validate** — percentages sum to 100%, exact amounts sum to the
   total, the payer is in the participant list (M5).
2. **Compute net balance** — for each expense, the payer is credited
   the full amount and every participant is debited their share.
   `net = total_paid − total_owed` (M2).
3. **Simplify debts** — a greedy algorithm pairs the largest creditor
   with the largest debtor, records a payment, and pushes remainders
   back onto the heaps until everyone is settled.  This runs in
   O(n log n) and produces a correct, near-minimal transaction set (M3).
4. **Report** — pretty-printed table or machine-readable JSON.

## Validation rules (M5)

| Check | Example failure |
|-------|-----------------|
| Payer is a participant | `payer 'X' is not a participant` |
| Percentages sum to 100% | `percentage splits sum to 85%, expected 100%` |
| Exact amounts sum to total | `exact split amounts (90) do not sum to total (100)` |
| No negative amounts | `exact split amount for 'A' is negative` |
| Non-empty participant list | `at least one participant is required` |

## Edge cases considered

- **Zero-amount expense** — accepted, produces no settlements
- **Single participant** — self-split, net always zero
- **Floating-point totals** — tolerance at 0.015 ₹ during validation
- **Unicode names** — properly handled
- **Duplicate participants** — deduplicated silently
- **Large amounts** — handled up to floating-point range
- **Partial failures** — invalid entries skipped; valid ones still processed
- **Empty input** — reported with clear error
- **Extra splits keys** — rejected for equal splits

## Performance

- **Balance computation**: O(e × p) where *e* = expenses, *p* = participants
- **Debt simplification**: O(p log p) using heaps
- **100 expenses with 3 participants**: < 1 ms

## Error handling

- CLI returns distinct exit codes: 0=ok, 1=file-not-found, 2=bad-json,
  3=permission, 4=wrong-type, 5=validation-warnings
- `process()` returns both `balances`/`settlements` and `errors` so
  callers can decide how to handle partial failures

## License

MIT