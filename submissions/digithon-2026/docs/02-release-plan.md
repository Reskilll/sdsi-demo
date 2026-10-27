# 02 · Release Plan: Nitro

> **Update (2026-10-25):** v0.1.0 (fixed pipeline) is built and tagged; see [architecture](04-architecture.md) and the [decision log](05-decision-log.md). The 30-site regression gates below are superseded by ADR-016 (test on a few brands). Agentic work follows ADR-013.

Assumes ~10 working days (D1–D10) and 3–4 people. Dates are relative until the Digithon deadline is confirmed. Compress or stretch by keeping the ordering and the cut lines.

## Principles

1. **Vertical slice first.** A crude end-to-end run (URL in, deck out) by D3 beats four polished agents that do not connect.
2. **The demo is the product.** Anything not visible on stage is cut first.
3. **Reliability over breadth.** One homepage, done well, on many brands, beats multi-page support.
4. **Cache and fallback by design.** Every external dependency has a stored result to fall back on.

## Workstreams and owners (suggested)

| Stream | Owner role | Scope |
|---|---|---|
| A. Orchestration and agents | Backend / AI engineer | Lead agent, run context, tools, tracing |
| B. Audit + Redesign | AI / frontend engineer | Playwright, Lighthouse, axe, GEO, brand kit, HTML generator |
| C. Experience | Frontend / designer | Command-centre UI, report card, before/after, ROI panel |
| D. Match + Deck + Demo | Product / delivery lead | Roster data, matcher, deck template, demo script, rehearsal |

## Releases

### R0: Foundations and spikes (D1–D2)
**Goal:** de-risk the three hardest unknowns and fix the architecture.

| Task | Done when |
|---|---|
| Repo, TypeScript monorepo (`apps/web`, `packages/agents`, `packages/tools`), CI lint + typecheck | `pnpm dev` runs web + worker |
| **Spike 1: render and fetch** any URL via Playwright, with a fetch ladder, SSRF guard, and screenshots at 3 widths | 20 of 25 test brand sites yield DOM + screenshots |
| **Spike 2: redesign quality**: brand kit extraction → single-file HTML, judged by the team on 5 brands | ≥ 3 of 5 rated "would show a CMO" |
| **Spike 3: latency and cost**: time and token budget per agent, model choices | Written budget; full run projected < 5 min, < $2 |
| Define the shared **run context schema** (Zod) and the SSE event contract | Schema merged; all streams code against it |
| Synthetic bench roster (30–40 developers) + schema | JSON loads in the matcher |
| Hardcoded org skill inventory `config/org-skills.json` (15–20 skills, realistic gaps) behind an `OrgSkillProvider` interface | Loads and validates; reviewed by the delivery lead for plausibility |
| `FeedEvent` schema + SSE contract (friendly line + detail layer, handoffs) | Schema merged; stub agents emit sample events into a throwaway feed UI |
| Test set of 30 brand sites, tiered (easy, normal, hard/bot-protected) | List committed with expected difficulty |

**Exit gate:** go/no-go on redesign quality. If Spike 2 fails, switch to the fallback approach (a curated component library plus LLM filling the copy and tokens).

### R1: Walking skeleton (D3–D4)
**Goal:** URL in, thin version of all four outputs out, through the lead agent.

- Lead agent plans, dispatches and merges. Sub-agents are stubs returning basic real data where cheap.
- Audit v0: Audit agent with the Speed, Mobile and Accessibility tool-skills (Lighthouse, Playwright, axe) and a plain scored report. The UX and GEO LLM inspectors arrive in R2.
- Feed v0: every agent emits `FeedEvent`s with deterministic template `friendly` lines; chat-style feed in the UI.
- Tool wrapper v0: `defineTool` / `defineSkill` auto-emit start/end posts from a per-tool `feed` spec (fun start pool, true-number end template); CI fails if a tool lacks one.
- Org match v0: hardcoded skills, formula implemented in code with unit tests.
- Redesign v0: brand kit → HTML, rendered in a sandboxed iframe.
- Match v0: skill tags → rank roster → naive estimate.
- Deck v0: fixed template, 6 slides, PPTX export.
- UI v0: URL box, four agent lanes with status, results tabs.
- Tracing: every run saved as a replayable JSON trace.

**Exit gate:** 3 different brand URLs complete end to end without manual intervention.

### R2: Feature-complete MVP (D5–D7)
**Goal:** all P0 requirements, at demo-acceptable quality.

| Area | Deliverable |
|---|---|
| Audit | All five inspectors in parallel (speed, mobile, a11y as tool-skills; UX vision and GEO as LLM inspectors). Synthesis step: grades, top-5 fixes with business impact, evidence links |
| Live feed | Persona-voiced `friendly` lines (fast model, template fallback), explicit handoffs and questions between agents, friendly/technical toggle, expandable detail with evidence, typing indicators, pinned "now" strip |
| Org match score | Gauge + per-skill breakdown, gaps and ready-by dates, "Why us" deck slide, links into the ROI panel |
| Redesign | Self-critique loop (vision review, ≤ 2 passes), responsive, clickable nav/hover, before/after slider |
| Match | Skill derivation from findings, ranked per role, rationale, effort and price estimate with assumptions |
| Deck | 8–10 slides, CMO narrative, numbers pulled from the context (single source of truth), PPTX + PDF |
| ROI | Interactive panel: idle devs, monthly cost, proposals/week, win rate → break-even |
| Platform | Progress streaming, per-agent retries, partial-result handling, timeouts, run cost display |

**Exit gate (Alpha):** 20 of 25 test brands produce a complete package in < 5 min; no P0 bugs open.

### R3: Hardening and polish (D8–D9)
**Goal:** make it reliable and beautiful. **Feature freeze at the start of D8** (bug fixes only after).

- Run the 30-site regression nightly and fix the top failure causes.
- Pre-warm and cache runs for 10 likely brands (see demo plan); build the "replay" mode that streams a saved trace with real timings.
- UI polish: motion, the "agents at work" view, typography, dark stage mode, large-screen legibility.
- Security pass: SSRF, iframe sandbox, secrets, rate limit.
- P1 items **only if** time allows, in this order: re-audit uplift → annotated change list → cover email → RFP intake.
- Record a full backup demo video.

**Exit gate (Beta):** ≥ 95% success on the 10 demo-list brands, ≥ 85% on the full 30; a fully offline replay works.

### R4: Demo release (D10)
**Goal:** a rehearsed, bulletproof showtime.

- Two full dress rehearsals, timed, on the actual venue hardware and network (or a hotspot).
- Freeze: tag `v1.0-demo`, deploy a known-good build, lock dependencies, rotate keys.
- Pre-flight checklist (see demo plan §7) completed T-60 min before showtime.
- Backup kit: replay mode, recorded video, exported decks for the 3 safest brands, a laptop with a local copy.

## Timeline view

```
Day   1  2  3  4  5  6  7  8  9  10
R0   ██ ██
R1         ██ ██
R2               ██ ██ ██
R3                        ██ ██
R4                              ██
Spikes ◆(D2 gate)  Skeleton ◆(D4)  Alpha ◆(D7)  Freeze ◆(D8)  Beta ◆(D9)  Demo ◆(D10)
```

## Cut lines (when time runs out, drop in this order)

1. Multi-viewport interactions in the prototype → keep a single responsive page.
2. P1 extras (cover email, annotated change list, RFP intake).
3. PDF export → keep PPTX only.
4. Self-critique loop → single-pass generation.
5. Live ROI interactivity → static slide.

**Never cut:** URL → audit → redesign → team → deck, the before/after reveal, the fallback/replay mode.

## Quality gates and test strategy

| Layer | Approach |
|---|---|
| Tools | Unit tests with recorded fixtures (HTML snapshots, Lighthouse JSON) |
| Agents | Schema validation of every output (Zod); "claim checker" test that every number in the deck exists in the run context |
| End to end | Nightly run over the 30-site set; report: success rate, p50/p95 latency, cost, screenshots for manual review |
| Visual | Human review board of before/after for the 10 demo brands; reject on broken layout or lost brand identity |
| Demo | Timed rehearsals; chaos drills (kill network, slow the API, blocked site) |

## Release risks (schedule-specific)

| Risk | Trigger | Response |
|---|---|---|
| Spike 2 shows weak redesigns | D2 gate fails | Switch to component library + token filling; budget +1 day |
| Agent stream flakiness | >10% run failures at D5 | Freeze new features; spend D6 on reliability |
| Team member unavailable | Any | Streams A and B are the critical path; D is the first to absorb extra work |
| Bot-blocking on target sites | Frequent in tests | Add a screenshot-only and cached-snapshot path; expand the pre-warm list |

## Definition of done (v1.0 demo)

- [ ] A URL pasted on stage yields audit, prototype, team + estimate and deck.
- [ ] Median run < 4 min, p95 < 6 min, with progressive reveal throughout.
- [ ] Before/after slider works on a projector-sized screen.
- [ ] Deck opens cleanly in PowerPoint and exports to PDF.
- [ ] Every number in the output is traceable to the run context.
- [ ] Replay mode and recorded video are ready as fallbacks.
- [ ] README with setup, env vars, and a one-command start.

## Post-demo roadmap (if it goes live at Samsung)

1. Real bench integration (HRMS / resource management); soft-hold and approvals.
2. CRM integration and send workflows with a human approval gate.
3. RFP-first mode and multi-page redesign.
4. Win/loss feedback loop to learn which audit angles convert.
5. Measure the real ROI: proposals per week, win rate, revenue, bench utilisation.
