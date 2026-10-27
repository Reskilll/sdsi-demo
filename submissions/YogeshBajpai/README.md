# Expense Splitter with Debt Simplification (Splitwise-lite)

Splits team-outing expenses three ways (equal, exact, percentage), shows each
member's net balance, and simplifies debts into a near-minimal list of
"A pays B ₹X" settlements.

## Requirements

- Python 3.9+ (standard library only — no dependencies).

## Usage

```bash
# Run the sample
python expense_splitter.py expenses.json

# Human-readable output (default), or machine-readable JSON:
python expense_splitter.py --json expenses.json

# Batch: pass several files at once
python expense_splitter.py a.json b.json c.json

# Pipe JSON on stdin
cat expenses.json | python expense_splitter.py -
```

## Input format (`expenses.json`)

```json
{
  "members": ["Amit", "Bina", "Chetan", "Diya"],
  "expenses": [
    { "payer": "Amit", "amount": 1000, "description": "Dinner",
      "split": { "type": "equal", "members": ["Amit", "Bina", "Chetan", "Diya"] } },
    { "payer": "Bina", "amount": 400, "description": "Taxi",
      "split": { "type": "exact", "amounts": { "Amit": 150, "Chetan": 150, "Diya": 100 } } },
    { "payer": "Chetan", "amount": 500, "description": "Tickets",
      "split": { "type": "percentage", "percentages": { "Amit": 50, "Bina": 30, "Diya": 20 } } }
  ]
}
```

- **equal** — optional `members` (defaults to the whole group); leftover paise
  are distributed one-at-a-time so the total is always exact.
- **exact** — `amounts` map; must sum to the expense `amount`.
- **percentage** — `percentages` map; must sum to 100 (fractional values like
  33.33 are accepted). The last member absorbs the rounding difference.
- A single expense object (not wrapped in a list) is also accepted.

## Validation

Rejected with a clear message: negative/zero/non-numeric amounts, percentages
that don't sum to 100, exact amounts that don't match the total, unknown or
duplicate members, a payer who isn't a group member, and unknown split types.

## Design notes

- **Integer paise** everywhere — money is stored as integer paise (₹1 = 100),
  so equal splits and percentage rounding never drift. `Decimal` is used only
  to parse input strings, not for arithmetic.
- **Greedy debt simplification** — repeatedly clears the largest debtor against
  the largest creditor. This yields at most `n - 1` settlements and is optimal
  whenever the optimal count is 1 or 2 (the usual cases); it is a
  near-minimal heuristic in the general NP-hard case.
- **One expense per call** — `add_expense` validates then commits, so a bad
  expense never corrupts earlier state.

## Running the tests

```bash
python -m pytest -q
# or, without pytest installed:
python -m unittest test_expense_splitter  # (pytest-style asserts)
```

## Security / robustness

- Input is parsed with `json` only; nothing is `eval`'d.
- Rejects non-finite numbers (`NaN`, `Infinity`) and boolean masquerades.
- Files are read with an explicit UTF-8 encoding; each file is capped by
  `json`'s structural parsing rather than a home-grown reader.
