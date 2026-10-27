# PROMPTS.md — AI Collaboration Log

How I worked with an AI coding assistant on PS6, what I accepted and what I
checked or changed myself.

## 1. Guardrails first
**Prompt:** Before writing any feature code, I set up a `claude.md` with project rules: security first (no hardcoded secrets, allow-list validation, fail closed, no stack traces in output), token-efficient answers (diffs over whole files) and testable, modular code.

**Why:** setting the standards up front made every later answer follow them without having to repeat them.

## 2. Problem framing
**Prompt (paraphrased):** "Here is PS6 (M1–M5 plus the judging criteria). Propose a short plan: language, architecture, edge cases and bonus features. Don't write code yet."

**Outcome:** I picked Python with the standard library only, for zero dependency risk and easy runnability. The design splits into calendar arithmetic, a status-timeline engine, a loader/validator and a reporter.

**My decision:** keep the business-calendar maths *pure* (naive local datetimes, no timezones inside) so it can be tested in isolation.

## 3. Defining semantics before code
I asked the AI to list the ambiguous rules and settled each one myself (see README → *SLA semantics*):
- Is a ticket breached when it finishes exactly on target? **No:** a breach is `elapsed > target`.
- What is "due-by" for a ticket that is on hold right now? **Project from `--as-of`, assuming it resumes now.**
- Does a deadline at closing time become 09:00 the next day? **No:** it stays at 18:00. This is easy to get wrong, so `test_lands_exactly_on_close` pins it down.
- What happens when a resolved ticket is reopened? **The clock resumes.** I generalised statuses into running / paused / stopped classes instead of hard-coding `ON_HOLD`.

## 4. Implementation prompts
- "Implement `BusinessCalendar.business_seconds` and `add_business_seconds` iterating per day, not per minute; guard against infinite loops."
- "Build status segments from history; ignore events after as_of; compute elapsed, paused and due-by in one pass."
- "Loader: strict allow-list validation; collect per-ticket errors instead of aborting; size limits; reject NaN and deep nesting; no stack traces."
- "Reporter: per-priority and per-group breach %; list priorities that have zero tickets with a null pct; neutralise CSV formula injection."

## 5. Verification (where the AI was not trusted blindly)
- Expected values for the sample tickets were **worked out by hand** and compared with the tool's output (for example INC-1003: 120 + 240 + 360 = 720 minutes, breached by 240).
- I asked for a **round-trip property test**: `business_seconds(t, add_business_seconds(t, s)) == s` across awkward starting times.
- I asked for **adversarial inputs**: path-like timezone names, a 500-character timestamp, terminal escape codes in a group name, 100k-deep JSON nesting, a BOM, duplicate ids.
- A performance guard test checks that a 5-year span stays fast.
- Windows check: IANA zones need `tzdata` there, so the sample policy uses a fixed offset and the README documents this.

## 6. What I'd prompt next
"Add a prefix-sum business-day index for O(1) interval queries" and "add first-response SLA alongside resolution SLA".
