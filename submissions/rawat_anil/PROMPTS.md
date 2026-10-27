# PROMPTS.md — AI Collaboration Log

How Claude Code was used to build the Expense Splitter.

---

## Prompt 1: Scaffold the architecture

> Build an Expense Splitter with three split types (equal, exact, percentage),
> net balance display, debt simplification, JSON input, input validation.
> Plan the file layout first.

**Outcome:** Claude proposed `models.py`, `validator.py`, `engine.py`, `cli.py`.
I agreed and asked it to implement.

## Prompt 2: Implement models and validator

> Write the dataclasses and validation logic. Catch: percentages must sum to
> 100, exact amounts to total, payer must be a member.

**Outcome:** `models.py` (Expense, Balance, Settlement, SplitResult) and
`validator.py` (validate_expense, validate_group_input) with 10+ specific
error messages.

## Prompt 3: Build the engine

> Compute balances from a list of expenses. Handle rounding for equal and
> percentage splits. Then implement greedy debt simplification — I want
> minimal "A pays B ₹X" settlements.

**Outcome:** `engine.py` with `compute_balances()` (handles rounding
absorption on last share) and `simplify_debts()` (greedy largest-debtor-
largest-creditor matching, O(n²) worst-case but fine for small groups).

## Prompt 4: Build the CLI

> argparse CLI that reads a JSON file. Support both single group and batch
> (array of groups). Pretty-print tables or output JSON with --json flag.

**Outcome:** `cli.py` with `load_expenses`, `process_group`, `format_result`,
and `main`. Batch mode, error collection, exit code 1 on validation failures.

## Prompt 5: Write tests

> 25+ test cases: cover M1 (all split types), M2 (net balances), M3 (simplify
> and verify settlements), M5 (validation errors), edge cases (rounding,
> large numbers, single-member groups, conservation of money).

**Outcome:** `test_expense_splitter.py` (unit) and `test_integration.py`
(e2e CLI). 100% pass rate on first run.

## Prompt 6: Polish with Claude

> Review the code for correctness, security, and completeness against the
> judgment criteria. Fix anything found.

**Outcome:** Minor fixes — added `round()` calls in settlement amounts for
float safety, added duplicate-member check in `validate_group_input`,
ensured `__main__.py` exists for `python -m` invocation.

---

## Key AI collaboration patterns

| What | How Claude helped |
|------|-------------------|
| Architecture | Proposed clean separation of concerns (models/validator/engine/cli) |
| Rounding edge cases | Identified that equal & percentage splits need rounding-error absorption; implemented last-share absorption |
| Debt simplification | Suggested greedy algorithm; I reviewed and accepted |
| Test coverage | Generated 25+ tests covering all criteria + edge cases in one pass |
| Docs | Wrote README.md and this PROMPTS.md from the codebase |

## What I learned

- Greedy settlement is simple and produces near-optimal results for typical
  group sizes (≤10 people). For exact optimality, the problem reduces to
  subset-sum (NP-hard), but that's overkill here.
- Rounding every intermediate result to 2 decimal places prevents
  floating-point accumulation bugs — a common pitfall in financial code.
- Validating early and collecting errors (instead of failing on the first)
  gives a much better UX for batch processing.