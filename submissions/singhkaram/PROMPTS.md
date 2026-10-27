# PROMPTS.md: AI collaboration log

Tool: **Claude Code** (Opus 5.5) in the Claude desktop app, working directly in the repository.

## 1. Initial prompt

> *(pasted the PS1 problem statement: M1–M5, judging criteria, "edge cases that aren't listed", plus a
> screenshot of the dashboard and the fork URL `github.com/singhkaram/sdsi-demo`)*

### What the AI did first
- Cloned the fork into its own folder and created the branch `ps1-expense-splitter`.
- Followed the repo README convention and put the work under `submissions/singhkaram/`.
- Set the commit author for this clone only.
- Chose **Java 21 + Maven**, because that toolchain was available and working on this machine.
- Chose a **command-line tool** rather than a web server. The problem is "process an expenses file and
  report", so a CLI is the most direct fit and the easiest for judges to run.

## 2. Design decisions

| Question | Decision | Why |
|---|---|---|
| How to store money? | `long` paise, never `double` | `0.1 + 0.2 != 0.3`; splits must add up to the exact paisa |
| ₹100 split 3 ways? | Largest-remainder method: 33.34 / 33.33 / 33.33, ties go to whoever is listed first | Exact total, deterministic, fair |
| Greedy settlement or optimal? | Exact subset DP for up to 20 non-zero balances, greedy above that | "Minimum" was the requirement; greedy alone is provably not minimal (example below) |
| Invalid expense in a batch? | Stop by default and list *all* problems with their positions; `--skip-invalid` opt-in | Silently dropping money records is worse than refusing |
| "Single or batch"? | `expenses` can be an array or one object, and the `add` command appends one expense | Covers both readings of M4 |
| "asha" vs "Asha"? | Member names unique ignoring case; references matched ignoring case | Avoids two different people who look like the same person |
| Repayments? | Recorded as an `exact` expense, so no new concept | Keeps the model small |

## 3. Iterations and corrections

1. **Greedy isn't minimal.** The first idea was "largest debtor pays largest creditor". The AI pointed
   out that greedy fails when there are independent zero-sum groups: `+100, +90, −90, −60, −40` takes
   4 transfers greedy, but 3 is optimal. This led to the subset-DP algorithm. The test
   `beatsGreedyWhenZeroSumGroupsExist` and the sample `data/greedy-vs-optimal.json` show the difference.
2. **Proving optimality, not claiming it.** A brute-force reference solver was added to the tests. The
   DP is checked against it on 1,500 random groups, using small values so zero-sum subgroups (the hard
   case) are common.
3. **Hindi names rejected (a bug found by a test).** The name pattern `\p{L}` rejected `आशा`, because
   Devanagari vowel signs are combining marks (`\p{M}`), not letters. The test `acceptsUnicodeNames`
   caught it, and `\p{M}` was added to the pattern.
4. **Validation that hides errors.** The first draft skipped the "shares must add up" check when another
   error existed, so users had to fix their file in several rounds. Now all checks run, and every problem
   is reported together.
5. **O(members) lookup per name.** The case-insensitive name lookup first looped over all members for
   every reference. It was replaced with a precomputed map.
6. **Jackson leniency.** Duplicate JSON keys were silently accepted, and `true` could be read as a
   number. Strict duplicate detection was turned on, and only numbers or numeric strings are accepted.
7. **Safe writes.** `add` first wrote the file in place. It now validates the whole file, writes to a
   temporary file and atomically moves it, so a crash or a rejected expense never touches the original.

## 4. Edge cases considered (each has a test)

- ₹100 / 3 people, ₹0.01 / 3 people, 15% / 85% of ₹0.10 (half-paisa tie)
- Percentages summing to 99.99 or 110; 33.3333 + 33.3333 + 33.3334
- Exact shares off by one paisa; zero shares; negative shares; 3-decimal amounts
- Payer outside the group; payer not among the participants (paying for others)
- Empty, duplicate or unknown participants; "Asha" vs "asha"
- Amount 0, negative, over ₹1 crore, 40-digit number, `true`, `"abc"`
- Unknown fields (`paidby`), duplicate JSON keys, wrong top-level types, empty file, missing file
- Single-member group, group with no expenses, everyone already settled
- 20 non-zero balances (the DP limit) under 5 s; 5,000 members via the greedy fallback

## 5. Verification

- `mvn test` → **72 tests, 0 failures** (see [TEST_REPORT.md](TEST_REPORT.md)).
- The packaged jar was run on both sample files, on a file with 10 different invalid expenses, and on a
  generated 5,000-expense file.
- Generated code was reviewed before committing; one real bug (Unicode names) was caught by tests and
  fixed.
