# PROMPTS.md — AI Collaboration Record

This file documents the prompts and AI iterations used to build the Expense Splitter.
It helps evaluators understand how AI was leveraged throughout development.

## Iteration 1: Initial scaffold
**Prompt:** "Create a Simple WebPage → Expense Splitter with Debt Simplification..."

**What the AI produced:** A self-contained single-file HTML app with all 5 requirements
(M1-M5): three split types, net balances, greedy debt simplification, JSON import,
input validation.

**Gaps found:** Percent validation passed raw percentages through to `buildExpense` before
`validateExpense`, defeating the 100%-sum check. Import rejected single objects.

## Iteration 2: Bug fixes + persistence
**Prompt:** "Check for gaps in the implementation against the master prompt"

**Fixes applied:**
- Moved percent conversion after validation (validate raw %, then convert to ₹)
- Accepted single-object imports in addition to arrays
- Fixed `removeMember` dangling-payer edge case
- Added `localStorage` persistence on every mutation
- Added Export-to-JSON with lossless percent round-trip via `_rawPct`

## Iteration 3: Comprehensive audit
**Prompt:** "Check for Functional correctness, Code quality, Testing, Documentation,
AI collaboration (PROMPTS.md), Security, Git hygiene, Performance, Error handling"

**Fixes applied:**
- **Security:** HTML-escaped all user data before `innerHTML` insertion
  (`escHtml`/`escAttr` helpers). Fixed XSS vectors in member names, expense
  descriptions, payer names in render functions.
- **Correctness:** `importJSON()` no longer mutates global `members` array before
  full validation passes — builds a `snapshot`, validates against it, then commits.
- **Export robustness:** Added fallback when `_rawPct` is missing (older localStorage data).
- **Magic numbers:** Extracted `EPSILON = 0.01` constant for all floating-point comparisons.
- **Documentation:** Created `README.md` and this `PROMPTS.md`.
- **Git:** Staged changes on `feature/rthakur869` branch.

## AI collaboration patterns

### What worked well
- **Incremental refinement:** AI traced through code line-by-line to find bugs
  (e.g., percent validation ordering) that wouldn't be obvious from a surface read.
- **Audit checklist:** Providing explicit categories (correctness, security, etc.)
  produced a thorough gap analysis.
- **Round-trip verification:** AI manually traced sample data through all functions
  to verify math correctness.

### What needed correction
- AI initially missed the percent-validation ordering bug — validated converted ₹
  amounts against a 100%-sum rule.
- AI initially used template literals with raw user data in `innerHTML`, creating
  XSS vectors.
- AI initially mutated global state (`members`) before full import validation.

### Recommended prompting pattern
For future AI-assisted builds on similar apps:
1. Start with full spec → get complete scaffold
2. Ask for a gap analysis against the spec (not "does it work?" but "where does it fail the spec?")
3. Ask for a security/robustness audit focused on XSS and state corruption
4. Generate README + PROMPTS.md after code is stable