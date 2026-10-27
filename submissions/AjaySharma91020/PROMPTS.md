# PROMPTS.md — AI collaboration log

## Session 1 — Initial build (2026-10-27)

### Prompt 1
> A team-outing expense settler (somewhat like Splitwise-lite). Build a C++ solution.

**Decision**: Used paise-based int64_t money model to avoid floating-point
issues — the gold standard for financial code. Built a minimal JSON parser
instead of adding dependencies. Used greedy max-heap/min-heap algorithm for
debt simplification (optimal for unrestricted variant).

### Prompt 2 (implicit from spec)
> M1–M5: three split types, net balances, debt simplification, JSON input, validation.

**Architecture**:
- `models.hpp` — plain structs (`Expense`, `Settlement`)
- `validator.cpp` — all M5 validation logic, returns `vector<ValidationError>`
- `engine.cpp` — `compute_balances()` and `simplify_debts()` (M2, M3)
- `json_loader.cpp` — bundled parser reads array or single object
- `cli.cpp` — `generate_report()` formats the output
- `main.cpp` — wires it together; `--validate` flag for validation-only mode

### Why C++
Chosen because the user explicitly requested it. Benefits: precise integer
arithmetic, no GC pauses, fast compilation, single-binary deployment.

### Edge cases considered
- Zero expenses → empty report
- Single-member expenses → net 0
- Rounding: equal split remainder goes to first N members; percentage remainder
  to last member; balances always sum to zero
- JSON safety: 10 MB file limit, only .json extension, UTF-8
- Duplicate members, negative amounts, payer-not-in-members all caught
- Percentage sum tolerance: ±0.01%
- Exact share tolerance: ±1 paisa

### Stretch decisions
- Bundled JSON parser (no external deps)
- Validation-only mode (`--validate`)
- Lightweight test harness (no Google Test dependency)
- Both batch array and single-object JSON input