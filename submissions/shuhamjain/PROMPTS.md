# PROMPTS.md — AI Collaboration Log

How the AI was used to build this submission, and how it shaped the result.
Each entry is the gist of the prompt given and what it produced.

---

## 1. Design before code

> "Read the problem statement and write a solution approach **before** writing
> any code — brief but with explanation, and recommend a stack."

**Outcome:** `solution.md`. The AI decomposed the five milestones (M1–M5) into a
small 3-path HTTP API, chose the data model (two tables + a counter), and
proposed Node.js + Fastify + SQLite. It also flagged the hidden edge cases
(open-redirect loops, IDN, scheme-bypass beyond `javascript:`) that the problem
hints at but doesn't enumerate.

## 2. Stack decision — human overrides the AI

> Original idea: Node.js backend + **Vue 2** frontend.

The AI recommended Vue 3 (Vue 2 is end-of-life) and TypeScript; the human chose
**Vue 2** and **plain JavaScript**. The AI recorded the trade-offs honestly in
`solution.md` and proceeded with the human's stack. *(Lesson: the AI flags
technical risk; the human owns the decision.)*

## 3. "Build it"

> "Now build the solution using Node.js (plain JS) + Fastify + SQLite; use Vue 2
> for the frontend if required."

**Outcome:** full backend — `base62` codec, URL validation/canonicalization,
idempotent shorten, resolve (302/410/404), stats, plus the Vue 2 dashboard
scaffold and a test suite.

## 4. Mid-course correction: backend first

> "You're not following the approach. Stop the frontend, restart with the
> backend first."

**Outcome:** the AI had started frontend files before the backend was verified.
The human's redirect focused effort: backend verified (tests green) before any
frontend work resumed. *(This is the single most useful collaboration beat —
the AI had front-loaded too much.)*

## 5. Build-environment failure → pivot

> Running `npm install` failed twice: first a TLS certificate error, then
> `better-sqlite3` couldn't compile (no Python on the Windows machine).

**Outcome:** the AI diagnosed both failures (not code bugs), then pivoted from
`better-sqlite3` to Node's **built-in `node:sqlite`** module (available in
Node 22). This removed the native-compilation dependency entirely — the whole
project now installs with zero native builds. It required rewriting `db.js` and
the transaction handling in `shorten.js` (`BEGIN`/`COMMIT` instead of
`.transaction()`).

## 6. Debugging the test suite

> "Fix the failing tests."

**Outcome:** iterative fixes — wrong require path (`./lib/...` → `../lib/...`),
a `node --test test/` glob that didn't match, a base62 alphabet expectation
(`Z` vs `z`), and a `shortUrl` assertion that the AI had changed to an absolute
URL. 16 → 19 tests green.

## 7. Hardening beyond the milestones

> "Do the remaining development."

**Outcome:** the AI added self-host/redirect-loop protection (reject URLs that
point back at the service), reserved-alias + TTL validation tests, the README,
and this log.

---

## What the AI was genuinely useful for

- **Domain edge cases** the problem only hints at (scheme-bypass, open redirect,
  canonicalization for idempotency, 302-vs-301 for analytics).
- **Build-tool triage** — distinguishing environment failures from code bugs and
  finding the zero-native-dependency path.
- **Ruthless decomposition** of the spec into testable units.

## What needed a human

- **Stack choice** (Vue 2 / plain JS) — a deliberate trade-off the AI can't make
  for you.
- **Sequencing** ("backend first") — the AI had over-invested in the frontend.
- **Security / credentials** — the AI correctly refused to handle a password in
  a shell command and steered toward PATs + forks instead.

---

*Generated as part of the SDSI submission; see `solution.md` for design and
`README.md` for run instructions.*