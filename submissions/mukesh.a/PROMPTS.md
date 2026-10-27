# PROMPTS.md — AI Collaboration

This document explains how the solution was built collaboratively with AI (Claude Code) and what prompts were effective.

## Approach

The Expense Splitter was built iteratively:

1. **Design first**: defined data models (Expense dataclass), validation rules, balance computation, and debt simplification algorithm on paper
2. **Core module**: implemented `expense_splitter.py` with all logic separated cleanly
3. **CLI + samples**: built `run.py` with `--sample`, `--batch`, and single-file modes
4. **Tests**: wrote comprehensive tests covering validation, edge cases, rounding, and end-to-end flows
5. **Documentation**: README.md with usage examples

## AI Prompts Used

### Intent 1 — Initial scaffold
> "Build an expense splitter with three split types (equal, exact, percentage), compute net balances, simplify debts to minimum transactions, validate inputs comprehensively, and include tests and README."

### Intent 2 — Edge-case hardening
> "Add tests for: rounding when 100 is split 3 ways, payer not in members list, single-person group, batch processing, invalid member in batch."

### Intent 3 — Debt simplification
> "Use greedy max-creditor matching for near-minimum transaction count settlement."

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `Decimal` for money | Avoids float precision issues in financial calculations |
| Greedy debt simplification | Minimum-transaction settlement is NP-hard; greedy is optimal for most practical cases and O(n log n) |
| Dataclasses | Immutable, self-validating models with clear serialisation |
| Zero dependencies | Pure Python standard library — no pip install needed |