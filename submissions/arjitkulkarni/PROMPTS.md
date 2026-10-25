# PROMPTS.md — AI collaboration log

Built with **Claude Code** (Claude Opus 5.5), working as an agent in the terminal.

## 1. Task prompt

> Go through all this, fork the repo on my GitHub, build something very small
> for this PS and give me the GitHub PR URL.

The prompt came with screenshots of the PS1 brief (M1–M5, E1–E3, the
multi-currency stretch goal, and the judging criteria) and of the PR
submission commands.

## 2. How the work was steered

| Step | What the AI did | Human/agent decision |
|---|---|---|
| Recon | Cloned the upstream repo and read its README | Followed the repo convention of building under `submissions/<alias>/` |
| Scope | Chose a zero-dependency Node CLI | "Very small" was taken to mean no framework, no UI, a pure core and a thin CLI |
| Money model | Integer paise plus a largest-remainder `allocate()` | Chosen before any split logic, so that E1 holds by construction rather than being patched in |
| Debt algorithm | Exact-match pairing followed by a greedy pass | The true minimum is NP-hard, so this documents the near-minimum trade-off instead of over-engineering |
| Validation | Collects **all** errors per batch | Better UX than failing on the first bad row |
| Tests | 33 `node:test` cases covering every M/E item, a randomised property test (always settles, ≤ n−1 transfers), a 10k-member performance test and CLI end-to-end tests | — |

## 3. Where the AI was wrong, and how it was caught

- The first currency test expected $10 split 3 ways to be ₹277.50 each.
  The test run failed. The code was right and the test was wrong: $10/3 is
  $3.34 / $3.33 / $3.33, so ₹832.50 is split in that ratio. The test was fixed
  to use $9, which splits evenly, and the uneven $10 case was kept as an
  explicit assertion.
- `node --test test/` behaves differently across Node versions (newer versions
  treat arguments as globs). It was changed to plain `node --test`, which
  auto-discovers `*.test.js` on Node 18 and later.

## 4. Verification

```
npm test                        -> 33 pass, 0 fail
node src/cli.js data/invalid.json -> 3 errors listed, exit code 1
```
