# Expense Splitter — SDSI Hackathon Submission

An expense splitting engine with debt simplification (Splitwise-lite).
Built for the SDSI Agentic AI Hackathon, developer track.

## Setup

```bash
# No external dependencies needed — uses only Python stdlib + pytest
pip install pytest   # only needed to run tests
```

## Run

```bash
# Process a JSON expense file
python -m expense_splitter.cli process submissions/Stoicall/samples/simple.json

# Or from project root:
cd submissions/Stoicall
python -m expense_splitter.cli process samples/simple.json
```

## Test

```bash
cd submissions/Stoicall
python -m pytest tests/ -v
```

## Input format (JSON)

```json
{
  "members": ["A", "B"],
  "expenses": [
    {
      "title": "Dinner",
      "total": 1000,
      "paid_by": "A",
      "split": {
        "type": "equal",
        "members": ["A", "B"]
      }
    }
  ]
}
```

Split types: `equal`, `exact`, `percentage`. See `samples/simple.json` for a complete example.

## Design choices

- **Decimal arithmetic** (stdlib `decimal.Decimal`) for exact monetary calculations — no float drift.
- **Greedy netting**: compute per-person net balance, then match largest debtor with largest creditor. This produces at most `N-1` settlements (optimal in the single-currency case).
- **Rounding**: remainder pennies are assigned to the first members (equal) or largest-percentage member (percentage) so the sum always equals the total.
- **Validation**: all inputs validated before recording; clear error messages.

## Assumptions

- Single currency (₹). No multi-currency support.
- All members are known upfront or discovered from expenses.
- The payer is always considered a member of the split (for equal/percentage/exact validation).

## Known gaps

- No undo/delete for expenses.
- No persistent storage beyond JSON files — full re-compute each time.
- Debt simplification is greedy, not min-transaction proof (but greedy matches the optimum for single-currency netting).
- No UI beyond the CLI report.

## Complexity

- Adding an expense: O(m) where m is number of members in that expense
- Net balances: O(e * m) where e = number of expenses
- Simplify: O(n log n) where n = number of members (sorting)