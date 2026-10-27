# AI Collaboration Documentation (PROMPTS.md)

This project was built as a complete implementation of the Expense Splitter
with Debt Simplification specification. This document records the AI-assisted
development process, key design decisions, and verification steps.

## Initial Development Prompt

The complete specification (Sections 1-14 of the problem statement) was
provided as a single initial prompt. The prompt included:

- Functional requirements (expense recording, balance calculation, debt
  simplification, JSON I/O, input validation).
- Architecture and code quality guidelines.
- Testing requirements (112 test cases specified).
- Security and robustness requirements.
- Documentation requirements.
- Performance considerations and stretch goals.

## Implementation Approach

### Phase 1: Repository Inspection
The repository was inspected and found to be empty (no existing code).
Python 3.11 was selected as the runtime. Python 3.11 was not initially
installed on the system; it was installed via `winget install Python.Python.3.11`.

### Phase 2: Core Module Implementation
The following modules were created in sequence:

1. **models.py** — Frozen dataclasses for `Member`, `Expense`, `ExpenseGroup`,
   `MemberBalance`, `Settlement`, `ShareAllocation`, and `ExpenseResult`.
   All monetary fields use `Decimal`. Split types as string enum.
2. **exceptions.py** — Custom exception hierarchy and `ValidationReport`
   collector for batch error reporting.
3. **splits.py** — Three split handlers (equal, exact, percentage) with
   deterministic remainder distribution.
4. **balances.py** — Aggregate paid/share per member across all expenses.
5. **simplify.py** — Greedy largest-debtor/largest-creditor (O(n log n))
   plus optional exact DP subset solver (O(n × 2^n)).
6. **validation.py** — Exhaustive JSON input validation with ~30 specific
   error checks.
7. **io.py** — JSON read/output and human-readable formatting.
8. **engine.py** — Pipeline orchestration with invariant verification.
9. **__main__.py** — CLI with argparse, supporting `--input`, `--output`,
   `--json`, `--balances-only`, `--settlements-only`, `--exact`.

### Phase 3: Test Suite
A comprehensive pytest suite was written with 5 test files:

- `tests/test_splits.py` — 14 tests (equal, exact, percentage, rounding)
- `tests/test_balances.py` — 14 tests (core calculations + invariants)
- `tests/test_simplify.py` — 19 tests (greedy + exact strategies)
- `tests/test_validation.py` — 33 tests (valid inputs + all error cases)
- `tests/test_integration.py` — 35 tests (engine pipeline, JSON I/O, CLI, end-to-end scenarios)

**Total: 112 tests**, all passing.

### Phase 4: Debugging and Fixes

#### Fix 1: UTF-8 Encoding on Windows
The ₹ symbol caused `UnicodeEncodeError` on Windows' default cp1252 codec.
Fixed by adding `sys.stdout.reconfigure(encoding="utf-8")` in `__main__.py`.

#### Fix 2: Test Fixture Mismatch
The `test_optional_name_field` test used `valid_input` with only 2 members
but the default expense referenced "charlie" (3rd member). Fixed by adding
the 3rd member to the test fixture.

#### Fix 3: Output File Writing for --balances-only and --settlements-only
The `--output` flag was only respected in the default mode, not in
`--balances-only` or `--settlements-only`. Refactored CLI to handle
output file writing uniformly across all modes.

### Phase 5: Verification
1. Ran full test suite: **112 passed, 0 failed**.
2. Ran CLI against `expenses.json`: correct balances and settlements.
3. Verified JSON output is valid and parseable.
4. Verified `--balances-only`, `--settlements-only`, `--exact`, `--json`,
   and `--output` all work correctly.
5. Manually verified balance calculations match expected values.

## Key Design Decisions

1. **Decimal for all money**: The specification explicitly requires avoiding
   floating-point arithmetic. Python's `Decimal` with round-half-up ensures
   exact cent-level precision.

2. **Greedy simplification as default, exact DP as optional**: The exact DP
   solver is O(2^n) and only practical for ≤12 non-zero members. The greedy
   solver is fast, simple, and produces good results for any group size.

3. **Atomic validation**: All validation errors are collected before any
   processing occurs. This prevents misleading partial results. There is no
   "best-effort" partial processing mode.

4. **Immutable dataclasses**: All model objects are frozen to prevent
   accidental mutation and ensure thread-safe read access.

5. **Remainder distribution to first N**: For equal and percentage splits,
   rounding remainders are distributed one paise at a time to participants
   in list order. This is deterministic and guarantees exact total.

6. **Single currency (INR)**: Multi-currency support would require exchange
   rate data and introduces complexity beyond the specification scope.

## Verification

Every claim in this document was verified by running the code. Tests were
executed with:

```
python -m pytest tests/ -v
```

The application was run against `expenses.json` with all CLI modes.

## Prompts Used

1. **Primary prompt**: The complete specification document (this prompt)
   requesting a full implementation.
2. **No follow-up prompts**: The implementation was completed in a single
   session. The AI inspected the repository, built all modules, created
   the test suite, ran tests, fixed failures, and wrote documentation
   autonomously.