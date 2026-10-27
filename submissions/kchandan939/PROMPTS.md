# PROMPTS.md — AI Collaboration Effectiveness

## Use case
Team-outing Expense Splitter (Splitwise-lite).  Python CLI + library that
reads a JSON list of expenses, computes net balances, and simplifies debts
into the fewest "A pays B ₹X" transactions.

---

## Prompt 1 — project scaffold

```
I need a Python project at submissions/expense-splitter/ with the
structure:

expense_splitter/
  __init__.py
  models.py        # Expense, Settlement, SplitType enums
  validation.py    # M5: validate input
  balance.py       # M2: compute net balances
  simplify.py      # M3: greedy min-txn simplification
  processor.py     # orchestration pipeline
  cli.py           # argparse-based entry point
tests/
  test_all.py
sample_expenses.json

The product is a Splitwise-lite: equal/exact/percentage splits,
input validation (percentages sum to 100, exact amounts sum to total,
payer in group), net balance per member, and debt simplification via the
greedy max-creditor-to-max-debtor algorithm.
```

---

## Prompt 2 — validation module (M5)

```
Write expense_splitter/validation.py that:

- Parses raw JSON dicts into Expense dataclasses
- For EQUAL: no splits dict allowed
- For EXACT: every split ≥0, sum of splits ≈ total (within 0.015 ₹)
- For PERCENTAGE: every split ≥0, sum ≈ 100%
- Payer must be in participants
- Negative total_amount → reject
- Empty participants → reject
- Batch validation returns a list of error strings, one per invalid entry
```

---

## Prompt 3 — balances module (M2)

```
Write expense_splitter/balance.py that:

- Takes a list of validated Expense objects
- For each expense, credits total_amount to the payer
- Distributes shares to participants per the split rule
- Returns {member: net} where +ve = owed money (creditor)
- Sanity: sum of all net balances ≈ 0
```

---

## Prompt 4 — settlement simplification (M3)

```
Write expense_splitter/simplify.py that:

- Takes {member: net} balances
- Ignores amounts within 0.005 ₹ (floating-point noise)
- Uses two max-heaps: creditors (largest positive first) and
  debtors (largest debt first)
- Greedily matches top creditor with top debtor, records payment,
  pushes remainders back
- Returns list of Settlement(from_member, to_member, amount)
- Empty list when all balances are zero
```

---

## Prompt 5 — CLI and processor

```
Write expense_splitter/cli.py and expense_splitter/processor.py.

cli.py:
- argparse: one or more file paths, --pretty (default), --json-out
- Reads JSON files (single object or array), merges into one list
- Returns process exit codes: 0=ok, 1=file not found, 2=bad JSON,
  3=permission, 4=wrong type, 5=validation warnings

processor.py:
- process(list[dict]) → SplitResult
- Skips invalid entries; processes valid ones together
- If all are invalid, returns empty balances with errors
```

---

## Prompt 6 — comprehensive tests

```
Write tests/test_all.py using pytest covering:

Validation:
- ok cases: equal, exact, percentage
- failures: payer not in group, sum mismatch, negative amounts,
  unknown split type
- batch: empty list, non-dict entry, mixed valid/invalid

Balances:
- equal, exact, percentage → correct net
- sum-zero invariant

Simplify:
- empty, single txn, multi creditor/debtor
- floating-point noise ignored
- transaction count ≤ (n - 1) for n participants

Edge cases:
- zero-amount expense
- single participant
- 100 equal expenses (performance sanity)
- floating-point totals (10.33 ÷ 3)
- Unicode names
- large amounts (1e9)
```

---

## Prompt 7 — README and polish

```
Write a README.md with:
- One-line description
- Project structure tree
- Quick start: pip install -e . && expense-splitter sample_expenses.json
- Sample JSON format with all three split types
- How it works (balance → simplify)
- Edge cases considered
```

---

## Prompt 8 — self-review against rubric

```
Review the code against the rubric:

M1 ✅ equal/exact/percentage all supported
M2 ✅ net balances via paid – owed
M3 ✅ greedy min-txn simplification
M4 ✅ CLI reads one or more JSON files (single or batch)
M5 ✅ validation rules enforced

Additional:
- All edge cases tested
- Git hygiene: atomic commits
- Security: validates input, no eval(), no pickle
- Performance: O(e·p) for balances, O(p log p) for simplify
- Typed Python with dataclasses
```

---

## Lessons learned

1. *Floating point* — monetary rounding needs explicit tolerance (0.015 ₹)
   in validation and comparison, plus 0.005 ₹ threshold in settlement to
   ignore noise.
2. *Greedy settlement* — the algorithm is O(n log n) and always produces a
   correct solution; it is a 2-approximation for minimum transactions.
3. *Partial processing* — invalid entries shouldn't block valid ones.
   Returning both results and errors is more useful than hard-failing.
4. *CLI exit codes* — differentiate file-not-found vs bad-json vs
   validation-warnings so scripts can branch on them.