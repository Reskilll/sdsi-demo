# 04 · How v0.1.0 works (architecture, in detail)

This document describes the **fixed-pipeline release (v0.1.0)**. It is the working fallback copy. Anything described here is implemented and was run end to end on `example.com` and `samsung.com/in`, in offline mode (no model key).

Companion docs: [decision log](05-decision-log.md) explains *why* each choice was made. [Requirements](01-requirements-analysis.md), [release plan](02-release-plan.md) and [demo plan](03-demo-plan.md) are the original plans.

## 1. What is real and what is fixed

This is the most important thing to understand about v0.1.0.

| Layer | Status | Detail |
|---|---|---|
| **Order of steps** | Fixed in code | The lead agent always runs: audit → (redesign ∥ bench match) → deck. Nothing decides the order at runtime. |
| **Parallelism** | Fixed in code | The five inspectors run in parallel; redesign and bench match run in parallel. |
| **Measurements** | **Real** | Every number comes from the live site: load timings, page weight, accessibility violations, tap targets, structured data, and so on. |
| **Findings and fixes** | **Real** (rule-driven) | Generated from the real measurements by fixed rules and thresholds. |
| **Brand kit and prototype** | **Real** content, template layout | Colours, fonts, logo, headlines, sections and images are extracted from the actual site. In offline mode the *layout* is a fixed template; the content is theirs. |
| **Re-audit of the prototype** | **Real** | The same inspectors are run on the generated page. |
| **Feed messages** | Written from templates | Start lines come from a pool of fun phrases per tool. End lines are templates filled with the real result, so the numbers are true. |
| **Org skills, bench roster** | **Sample data** | `config/org-skills.json` and `config/bench.json` are invented for the demo. |
| **Org match score, team, estimate** | Real computation on sample data | The formulas run for real. Their inputs (skills, people, rates, day counts, margin) are assumptions. |
| **ROI panel** | Placeholders | Defaults are made up and editable. |
| **Model (LLM) calls** | Not exercised yet | Three places call the model when `ANTHROPIC_API_KEY` is set. They have never run in this environment. In offline mode, rule-based fallbacks run instead. |

So: **the sequence is hardcoded, the results are computed from the real site.** Nothing in the audit or prototype is pre-baked per brand.

## 2. Components and request flow

```
 Browser (web/index.html)                    Node server (src/server.ts)
 ─────────────────────────                   ──────────────────────────────────────────
 1. POST /api/runs {url}  ───────────────▶   validate URL (SSRF guard) → create RunContext
                                             start runLead(run) in the background
    ◀── {runId}
 2. GET /api/runs/:id/events (SSE) ──────▶   replay past events, then stream new ones
    ◀── data: {FeedEvent}  … one per step
 3. render feed, lanes, panels
 4. <img src=/runs/:id/shot-*.png>  ─────▶   static files from ./runs/:id/
    <iframe sandbox src=/runs/:id/prototype.html>

                  runLead (src/agents/lead.ts)
                    ├─ runAudit        → browser.render, then 5 inspector skills in parallel
                    ├─ runRedesign ┐   (in parallel)
                    ├─ runBench    ┘
                    └─ runDeck
                          │ every tool/skill call goes through defineTool → posts to RunBus
                          ▼
              Playwright → headless Chromium (one process, shared)
```

- **One Node process** serves the UI, the API and the files, and also launches Chromium. There is no separate backend service.
- **Playwright runs only on the server.** The browser page never runs it; it only displays results.
- **Streaming uses Server-Sent Events** (see ADR-006).
- **State** lives in memory (`Map<runId, RunContext>`) and is also written to disk: all artefacts in `runs/<runId>/`, plus `trace.json` (every feed event) when a run ends.

## 3. Module map

| Path | Responsibility |
|---|---|
| `src/server.ts` | HTTP server: start run, SSE stream, static files, `/api/config`. Caps concurrent runs at 3. |
| `src/cli.ts` | Headless run for testing; prints the feed to the terminal. |
| `src/core/events.ts` | `FeedEvent` type, agent personas, `RunBus` (event log + subscribers). |
| `src/core/tool.ts` | `defineTool`: wrapper that makes every tool/skill post start/end/retry/error to the feed. |
| `src/core/context.ts` | `RunContext`: run id, output folder, bus, shared data. |
| `src/core/types.ts` | Data shapes: `CrawlData`, `Finding`, `AuditReport`, `BrandKit`, `MatchResult`, … |
| `src/core/ssrf.ts` | URL normalisation and private-address blocking. |
| `src/core/scoring.ts` | Grades and linear scoring helpers. |
| `src/core/orgMatch.ts` | Org skill provider interface, hardcoded provider, org match formula. |
| `src/core/llm.ts` | Anthropic client; returns `null` without a key so callers use fallbacks. |
| `src/tools/browser.ts` | Chromium launch, `browser.render` (the crawl), page extraction. |
| `src/tools/inspectors.ts` | The five inspector skills (speed, mobile, a11y, UX, AI-search). |
| `src/agents/audit.ts` | Runs the crawl and inspectors, synthesises the report card. |
| `src/agents/redesign.ts` | Brand kit, prototype generation, screenshot, re-audit. |
| `src/agents/bench.ts` | Roster load, org match, team selection, estimate. |
| `src/agents/deck.ts` | PPTX deck and markdown proposal. |
| `src/agents/lead.ts` | The orchestrator: fixed sequence, handoffs, graceful degradation. |
| `config/` | Hardcoded sample org skills and bench roster. |
| `web/index.html` | The whole UI: lanes, feed, panels, ROI, idle-cost ticker. |

## 4. The run, step by step

### 4.1 Lead (`runLead`)
1. Posts the plan ("New case!").
2. Runs the audit. If the audit fails entirely, the run stops with an error (nothing to build on).
3. Posts handoffs to Redesign and Bench, then runs both with `Promise.allSettled`. If one fails, the run carries on with a warning.
4. If both the brand kit and the match exist, hands off to the deck agent. Otherwise it skips the deck and says so.
5. Posts `done` with the elapsed seconds.

### 4.2 Audit (`runAudit`)
1. **`browser.render`** opens the site in desktop Chromium (1440×900). Before load it injects observers for LCP and CLS, and attaches a Chrome DevTools Protocol listener to total up transferred bytes and request count. After load it hides fixed cookie/consent overlays, extracts the page (see 4.3), takes the desktop screenshot, and fetches `/robots.txt` and `/llms.txt`.
2. **Five inspectors run in parallel**, all given the same crawl snapshot:

| Inspector | How the score is computed |
|---|---|
| **Speed** | `0.40×LCP + 0.20×CLS + 0.25×page weight + 0.15×request count`, each scaled linearly between a "good" and a "poor" threshold (LCP 2.5–4.5 s, CLS 0.1–0.25, weight 1.5–6 MB, requests 60–200). Falls back to the page-load time if LCP was not reported. |
| **Mobile** | Reloads at 375×812 with a phone user agent and touch. Starts at 100; −35 if no viewport meta; −25 if the page is wider than the screen; up to −30 for small tap targets (< 32 px); up to −15 for text < 12 px. Saves a mobile screenshot. |
| **Accessibility** | Injects axe-core into the page and runs it. Penalty per rule = impact weight (critical 8, serious 5, moderate 2, minor 1) × min(3, elements affected). Score = 100 − total penalty. |
| **UX** | With a key: a vision model scores a screenshot on five criteria (hierarchy, CTA clarity, navigation, trust, copy) 1–5. Without a key: rule-based heuristics (number of h1s, CTAs above the fold, nav items, hero text length, structured data present). Score = average ÷ 5 × 100. |
| **AI-search** | Points: structured data present 25, organisation-type schema 10, `llms.txt` 15, AI crawlers not blocked in robots.txt 15, meta description 10, exactly one h1 10, "answerability" 1–5 mapped to 15. Answerability comes from a model when a key is set, otherwise from description length and h1 count. |

3. **Synthesis:** overall = weighted average (speed 20%, mobile 20%, accessibility 20%, UX 25%, AI-search 15%). Top fixes = all findings sorted by severity then category weight, at most two per category, first five. Grades: A ≥ 90, B ≥ 80, C ≥ 65, D ≥ 50, else F.
4. If one inspector fails, it is skipped and the overall score uses the remaining weights.

### 4.3 What the page extraction collects
Title, meta description, language, viewport meta, h1s, h2/h3 sections (heading + nearby paragraph), up to 8 nav links (skip links removed), above-the-fold CTAs (links/buttons matching action words), large images with alt text, image count and missing alt, logo, social image, brand colours (most frequent saturated mid-tone among buttons, links and headings; background and text colour from the body), fonts, JSON-LD blocks, hero text, a sample of body text, script count, and the timing metrics.

### 4.4 Redesign (`runRedesign`)
1. **Brand kit** is assembled from the extraction (no model needed).
2. **Prototype:** with a key, a model is asked for one self-contained HTML file given the brand kit and the top fixes. Without a key, a fixed template is filled with the extracted content: skip link, sticky header with logo, nav and CTA, hero with headline, supporting copy and image, "why" cards from the site's own sections, gallery, closing CTA band, footer, JSON-LD, mobile menu without JavaScript, 44 px tap targets, reduced-motion support, and a "concept redesign" ribbon. The button colour is darkened if it would fail contrast.
3. The file is saved, served by the same server, and **screenshotted** for the "after" image.
4. **Re-audit:** accessibility, mobile and UX are run again against the prototype URL (v0.2 re-runs the same vision review for UX). **Speed and AI-search are deliberately not re-run** (a local file would be a meaningless speed comparison, and robots.txt/llms.txt belong to the site). In v0.1.0, AI-search was re-run at page level.
5. The panel shows before/after, the score changes and the change list (each change maps to the audit finding it addresses).

### 4.5 Bench match (`runBench`)
1. **Needed skills:** a fixed baseline (Next.js 0.8, responsive UI 0.7, UX design 0.7, QA 0.5, project management 0.5) merged with skills named by the audit findings. A finding's skills are weighted by `sum of severities / 6`, clamped to 0.3–1.
2. **Org match score** (deterministic): for each needed skill, `fit = 0.6 × proficiency + 0.4 × depth`, where proficiency = `min(level, 4)/4` and depth = `min(1, available ÷ needed headcount)`; needed headcount is 2 for weight ≥ 0.8, else 1. Score = `100 × Σ(weight × fit) / Σ(weight)`. Strengths are fit ≥ 0.85; gaps are fit < 0.5.
3. **Team:** for each needed skill, heaviest first, pick the highest-level free developer with that skill who is not already picked, up to six. Fit blends their level and how much of the needed skill-weight they cover.
4. **Estimate:** days per finding by severity (minor 2, moderate 4, severe 7), plus 15 days for the homepage rebuild, plus QA (15%) and delivery management (10%). Weeks = total days ÷ team size ÷ 5 (minimum 2). Price = days × average day rate of the chosen team × 1.4 margin, shown as a range of −10% to +15%.
5. **Idle cost recovered** = team size × weeks × 5 days × average rate × 0.6 (loaded-cost factor).

### 4.6 Deck (`runDeck`)
Nine slides built with pptxgenjs, reading only from the run data: title, site today (score bars), top fixes with business impact, before/after screenshots, proof (score changes and change list), plan (workstream bars), why us (org match score, team, gaps), investment (price range and assumptions), next steps. A markdown proposal is written alongside. The proposal's terms section is an explicit placeholder. Nothing is sent anywhere.

## 5. The live feed

- Every tool and skill is created with `defineTool`, which requires a `feed` spec: a list of start lines, an end-line function over the real result, an error line, and optional detail text. A tool without it does not compile.
- On each call the wrapper posts `tool_start` (or `skill_start`), then `tool_end`/`skill_end` with duration and outcome. On failure it posts a warning and retries once; after the final failure it posts a failure line and rethrows.
- Start lines rotate so the same phrase is not reused within a run, while the pool lasts.
- Agents also post status, handoff, question/answer, finding, partial-result, warning and done events directly.
- The UI pairs each start with its end into one line (spinner → tick), groups lines by agent persona, supports a Friendly/Technical toggle and expandable details, and fills panels from `partial_result` events.
- All text from the prospect's site is HTML-escaped before display.

## 6. Output files per run (`runs/<runId>/`)

`shot-desktop.png`, `shot-mobile.png`, `prototype.html`, `shot-after.png`, `shot-mobile-after.png`, `pitch-deck.pptx`, `proposal.md`, `trace.json`. The `runs/` folder is git-ignored.

## 7. Known limitations (honest list)

1. **Speed numbers are un-throttled** Playwright measurements on a fast laptop, so they will look better than Lighthouse's mobile profile. Lighthouse is planned.
2. **Model paths untested:** vision UX review, AI-search judgement and model-designed prototype have never run.
3. **Offline UX and AI-search scores are crude heuristics.** They are computed, but a human would judge more finely.
4. **Template redesign is generic.** It keeps the brand's content and colours but not its visual personality.
5. **Org match is not differentiated by industry,** so scores tend to be high. Real demo variety needs prospect-type skills (commerce, regulated industries, and so on).
6. **SSRF guard checks only the initial URL.** A redirect to a private address, or subrequests from a page, are not blocked. Fine on a presenter laptop, not for hosting.
7. **Everything is in memory:** a server restart forgets runs (files remain on disk). There is no replay mode yet.
8. **Bot-protected sites** may block the crawl. The retry is one extra attempt; there is no screenshot-only fallback yet.
9. **PDF export, RFP intake, persona-rewritten feed lines** are not built.
10. **Development workarounds** (documented in the decision log): Chromium fallback to the newest cached build, and a `__name` stub so functions run inside pages under `tsx`.

## 8. How to run (v0.1.0) and how to fall back

```bash
npm install
npm start                                   # UI at http://localhost:3000
npm run cli -- https://example.com          # headless run, feed printed
git checkout v0.1.0                         # return to this working copy at any time
```

`v0.1.0` is a git tag on the commit that contains exactly what is described here. Agentic work happens on a separate branch (see ADR-013), so this version stays intact.

## 9. v0.2 changes (branch `v0.2-agentic`)

These changes are on top of everything above. See ADR-018 to ADR-021.

1. **Planner-driven lead.** The lead is now a loop (`executePlan` in `src/agents/lead.ts`): state summary → planner decision → run steps → record → repeat. With no API key, or `NITRO_LEAD=fixed`, the **RulePlanner** is used and the flow is exactly v0.1.0's. With a key, the **LlmPlanner** chooses; guardrails in `validateDecision` (known steps, prerequisites, attempt limits, 8-round budget, no early finish) reject invalid choices and the rule planner takes over for that round. The lead posts the planner's one-line reason to the feed as a status message, with the full decision in the details.
2. **Adaptive retry.** If the prototype's re-audit shows any category got worse, and a model is available, the redesign step is retried once with feedback ("scores dropped in: mobile").
3. **Lighthouse speed.** Speed uses Lighthouse 12 (mobile, simulated throttling) in its own headless Chrome, with the Playwright method as fallback. Typical run time rises to about 30 s on heavy sites.
4. **`.env` loading** for `ANTHROPIC_API_KEY` and options (see `.env.example`).
5. **Tests:** `npm test`.

6. **Model path validated live** on allbirds.com and stripe.com (ADR-022): streaming prototype generation with progress posts, fair before/after (accessibility, mobile and UX are re-audited; speed and AI-search are not), CSP-safe accessibility checks.

7. **Replay mode** (ADR-023): every run saves `trace.json`; the UI defaults to replaying saved runs for free, with Live as an explicit switch. `npm run replay` does the same in the terminal.

8. **Tech stack analysis** (ADR-024): HAR-style request log, signature-based technology detection, third-party traffic stats, and coverage of the prospect's stack against our org skills; new Tech Detector agent and Tech stack tab.
9. **Feed UI** (ADR-025/026): newest first, headline-number tiles, screenshots in the feed, plain agent names, light and dark themes, slower replay.

10. **Pixel office and review window** (ADR-028): robot avatars, an event-driven animated office on the main screen, and a separate review window for the report tabs, opened from a post at the end of the run.

Still not built: PDF export, RFP intake.

## 10. Falling back

`git checkout v0.1.0` returns to the fixed pipeline at any time. On this branch, `NITRO_LEAD=fixed` and `NITRO_LIGHTHOUSE=0` reproduce v0.1.0 behaviour.
