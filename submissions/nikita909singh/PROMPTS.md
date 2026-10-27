# PROMPTS.md: AI collaboration log

Tool: **Claude Code** (Opus 5.5) in the Claude desktop app, working directly in the repository.

## 1. Initial prompt

> *(pasted the PS6 problem statement: M1–M5, judging criteria, "edge cases that aren't listed", plus a
> dashboard screenshot and the fork URL `github.com/nikita909singh/sdsi-demo`)*

### What the AI did first
- Cloned the fork into its own folder and created the branch `ps6-sla-tracker`.
- Followed the repo README convention and put the work under `submissions/nikita909singh/`.
- Set the commit author for this clone only.
- Chose **Java 21 + Maven**, the toolchain available on the machine. `java.time` handles time zones
  and daylight saving correctly, which matters for a deadline calculator.
- Chose a **command-line tool**. The task is "read three JSON files, compute, report", so a CLI is the
  most direct fit and the easiest for judges to run.

## 2. Design decisions

| Question | Decision | Why |
|---|---|---|
| How to count business time? | Walk day by day; for each working, non-holiday day, intersect the interval with that day's 09:00–18:00 window | Simple, obviously correct, O(days) |
| Precision? | Seconds internally; elapsed is rounded down to minutes, breach minutes rounded up | A 30-second breach must still show as a breach (≥ 1 min) |
| Exactly on target? | Not a breach (`elapsed > target`) | "Within 4 hours" includes 4:00:00 |
| Target used up at exactly 18:00? | Due-by = 18:00, not next day 09:00 | That is when the time actually runs out |
| Due-by for an on-hold ticket? | Shown as `(paused)` unless it's already late | The real deadline depends on when work resumes; inventing one would be wrong |
| Reopened tickets? | The clock resumes and elapsed time adds up | Otherwise reopening would reset the SLA |
| "As of" for open tickets? | `--as-of`, default now; later events ignored | Reproducible reports and tests |
| Breach % denominator? | All tickets, open count shown alongside | Transparent; documented in the README |
| Invalid tickets? | Stop by default and list all; `--skip-invalid` opt-in | Silently dropping tickets would understate breach % |

## 3. Iterations and corrections

1. **Hand-checked expectations first.** The sample `tickets.json` was designed so each ticket shows one
   rule (holiday, weekend, hold, reopen, at risk, …). The expected result for every ticket was worked
   out by hand *before* running the code, and the tests assert those numbers.
2. **Due-by for RESOLVED → CLOSED (a bug found by that check).** The first version projected the
   due-by of a resolved ticket from its *last* status change. T-1007 (resolved Thursday 16:00, closed
   Friday 10:00) came out due Monday 10:00 instead of Friday 16:00. Fixed by remembering the moment the
   ticket was first resolved.
3. **Adding zero business minutes outside hours (a bug found by a test).** `addBusinessSeconds(20:00,
   0)` returned the next morning at 09:00. Zero minutes after a moment is that moment, so this was fixed.
4. **Custom status names.** A policy that calls its running status `WORKING` instead of `OPEN` made new
   tickets start with the clock stopped. The starting status is now taken from the policy.
5. **Summary logic.** The first draft worked out "is this ticket still open" from hard-coded status
   names. It was replaced with a `resolved` flag on each result, so custom status names work end to end.
6. **CSV injection.** An assignee group like `=HYPERLINK(...)` would run as a formula in Excel. The
   group-name allow-list rejects it on input, and CSV cells starting with `= + - @` are also escaped.
7. **Readable errors.** "Created after as-of" first printed the time in UTC. It now uses the policy's
   time zone.

## 4. Edge cases considered (each has a test)

- Ticket raised on a weekend, after 18:00, before 09:00, or on a holiday
- Due-by landing exactly at 18:00; due-by pushed past a holiday (T-1010 skips 20 Oct)
- Resolved exactly on target vs 1 second late
- ON_HOLD over a weekend; several holds; hold at creation; breach that happened before a hold
- RESOLVED → CLOSED; RESOLVED → REOPENED → still open
- Status changes after `--as-of`; ticket created after `--as-of`
- DST change (America/New_York, March 2026) over a weekend
- Unsorted history; history before `createdAt`; unknown status; local times without an offset
- Unknown priority, duplicate ids, missing id, unknown fields, duplicate JSON keys
- Impossible policies: start ≥ end, no working days, negative or non-minute targets, bad time zone
- 20,000 tickets; tickets open for three years

## 5. Verification

- `mvn test` → **84 tests, 0 failures** (see [TEST_REPORT.md](TEST_REPORT.md)).
- The packaged jar was run on the sample data (text, JSON, CSV), on a file with 10 differently broken
  tickets, on a bad holidays file, and on a generated 20,000-ticket file.
- Generated code was reviewed before committing. Two real bugs were caught by the hand-calculated tests
  and fixed (items 2 and 3 above).
