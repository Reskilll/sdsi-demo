# PROMPTS.md — AI Collaboration Effectiveness Log

This document records the prompt-design methodology and collaboration patterns used
to build this project with Claude Code. It serves as evidence for the "AI
collaboration effectiveness" judging criterion.

---

## Session 1: Architecture Blueprint

**Prompt strategy**: "Act as Principal Software Architect. Before writing any
execution code, analyze the core requirements and design a complete, object-oriented
system blueprint."

**Why this worked**: Gave the AI a role frame (Principal Software Architect),
explicitly forbade premature implementation, and demanded holistic design before
any code. The resulting `ARCHITECTURE.md` captured the Strategy pattern for splits,
the max-heap settlement algorithm, Decimal precision policy, and batch error
collection strategy — all before a single line of Python.

**Key decisions from this prompt**:
- Split as an ABC → open/closed for future split types
- GroupManager as aggregate root owning members + expenses
- JSONProcessor as Command Processor pattern for batch mode
- Greedy max-heap O(n log n) for debt simplification

---

## Session 2: Edge Case Deep Handling (5 cases)

**Prompt strategy**: Listed 5 specific edge cases, demanded "Highly professional,
analytical, structured" analysis with no "conversational fluff."

**Why this worked**: The prompt enumerated all edge cases explicitly — no hunting
needed. The "no conversational fluff" directive produced dense, technical output.
The response format requirement (4 numbered sections) forced disciplined structure.

**Key decisions from this prompt**:
- Soft-delete with `Member.active` flag → preserves historical referential integrity
- `validate_amount()` centralised guard with sub-paisa check (`as_tuple().exponent`)
- `MONEY_CONTEXT` with `prec=28` → public constant, not hidden
- Cyclical debts handled naturally by net-balance approach
- Self-payment legalised (≥1 participant, was ≥2)

---

## Session 3: Comprehensive Judging Criteria Audit

**Prompt strategy**: Supplied all 9 judging criteria verbatim from the organisers,
requested a full gap analysis, and instructed to find edge cases "not listed here."

**Why this worked**: Providing the exact criteria let the AI map each one to
specific code — PROMPTS.md missing → generate it, .gitignore missing → create
it, etc. The "not listed" instruction triggered proactive thinking about:
duplicate participants, negative exact amounts, zero percentages, NaN in JSON.

**Key decisions from this prompt**:
- `PROMPTS.md` (this file) created from scratch
- `.gitignore` created with Python-standard patterns
- Duplicate-participant validation added to `split_from_dict()`
- Member name validation: max 100 chars, no control characters
- Whole-number member count cap (10,000)
- Negative exact amount guard, negative percentage guard
- Zero-percentage participant test
- 1000-member stress test added to settlement
- Security: JSON size limit (50MiB), no nested bombing

---

## Prompt Design Principles Used

### 1. Role framing
Every prompt begins by naming a role ("Principal Software Architect", "Senior
Engineer performing a quality audit"). This constrains the AI's register and
depth. Roles with authority ("Architect", "Principal") produce more confident,
opinionated output than roles without ("write code for...").

### 2. Explicit enumeration
Vague prompts ("handle edge cases") produce vague output. Each edge case was
named and numbered. Each judging criterion was quoted verbatim. The AI matched
items 1:1.

### 3. Output format specification
Demanding "no conversational fluff" and a structured 4-section response format
eliminated filler. The README and ARCHITECTURE sections were prescribed by name.

### 4. Progressive refinement
Session 1 → architecture. Session 2 → edge-case hardening. Session 3 → audit
against judging criteria. Each pass deepened the prior work rather than
rewriting it. At no point did the AI restart from scratch.

### 5. Error-first thinking
Every session began by *finding problems*. The first draft was never accepted
as final. The AI was directed to audit, find gaps, and fix — before asking
for approval. This produced a more thorough result than "review this" would
have.

---

## Prompt-to-Code Traceability Matrix

| Requirement | Prompt Text | Implementation |
|-------------|------------|----------------|
| M1: Add expenses | "Add expenses (Equal, Exact, Percentage splits)" | `src/models/split.py` — Split ABC + 3 subtypes |
| M2: Net balances | "Track and display net balances per member" | `src/services/balance.py` — BalanceCalculator |
| M3: Simplify debts | "min transactions via a greedy max-flow/heap algorithm" | `src/services/settlement.py` — SettlementEngine |
| M4: Batch JSON | "Batch/Singular processing from JSON files" | `src/services/json_processor.py` — JSONProcessor |
| M5: Validation | "percentages = 100%, exact amounts = total, valid payer" | `src/models/split.py` validate_invariants, `validate_amount()` |
| Edge 1: Fractional | "Floating-Point Precision: fraction paise/cents" | `_compute_shares()` residue absorption, cached shares |
| Edge 2: Scale/Decimal | "Using exact numeric types like Decimal" | `MONEY_CONTEXT`, `validate_amount()`, sub-paisa check |
| Edge 3: Cyclical | "Cyclical Debts & Net-Zero members" | Heap algorithm filters `|net| ≤ EPSILON` |
| Edge 4: Self-pay | "A paying for A, empty groups, single-member" | Relaxed ≥1 participant/member constraints |
| Edge 5: Deleted members | "Inactive/Deleted group members mid-history" | `Member.active` flag, `deactivate_member()` with tombstone |
| Unlisted: Dups in split | — | `split_from_dict()` len check against set |
| Unlisted: Neg amounts | — | `validate_amount()` ≤0 check, ExactSplit amounts ≥0 |
| Unlisted: Neg pcts | — | `PercentageSplit._validate_invariants()` sum=100, individual≥0 |
| Unlisted: NaN/Inf | — | `validate_amount()` Decimal(str()) catches NaN/Inf |
| Unlisted: Large JSON | — | `JSONProcessor` 50MiB file size cap |
| Unlisted: Name length | — | Member name max 100 chars, no control chars |