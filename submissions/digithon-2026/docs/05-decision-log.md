# 05 · Decision log

One entry per decision: context, options, choice, consequences. Newest decisions go at the bottom. Status is **Accepted**, **Superseded**, or **Proposed**.

---

## ADR-001 · Plain Node server and one static page, not Next.js
**Date:** 2026-10-25 · **Status:** Accepted (revisit for v0.2 if the UI grows)

**Context.** The plan assumed a Next.js UI plus a Node agent runtime. We needed a working end-to-end demo quickly, and the UI is a single screen.
**Options.** (a) Next.js app with API routes; (b) Node `http` server plus one HTML file with vanilla JS.
**Decision.** (b).
**Why.** Fewer moving parts (no build step, no framework upgrade risk, instant restart), and the same behaviour. The server must stay running for long jobs and own a Chromium process, which fits a plain Node process better than serverless-style API routes.
**Consequences.** The UI is hand-written DOM code in one file and will get harder to maintain as it grows. Migrating later to React/Next.js is possible because the UI only depends on the HTTP and event contract.

## ADR-002 · npm workspaces avoided; single package, npm (not pnpm)
**Status:** Accepted
**Context.** `pnpm` is not installed on the laptop; the plan proposed a monorepo.
**Decision.** One package at the repo root, managed with npm, TypeScript run through `tsx`.
**Why.** The fewer installs and config files the better for a hackathon, and a monorepo split adds no value at this size.
**Consequences.** Code is organised into folders (`core`, `tools`, `agents`) rather than packages. Can be split later.

## ADR-003 · Scripted orchestration, and the Anthropic Messages API directly, not the Claude Agent SDK
**Status:** Accepted for v0.1.0. **Partly superseded by ADR-020 on the v0.2 branch** (a planner now chooses steps; the Agent SDK is still not used).
**Context.** The pitch calls the lead a "God agent". The question is whether a model decides the steps at runtime.
**Options.** (a) Claude Agent SDK, lead agent decides which tools and sub-agents to run; (b) our own code runs a fixed sequence and calls the model only for judgement.
**Decision.** (b) for v0.1.0. The order of steps and the parallelism are hardcoded in `src/agents/lead.ts`. The model (when a key is set) is called in three places only: UX vision review, AI-search answerability, prototype HTML.
**Why.** Predictability for a live demo: same steps, same timing, fewer ways to fail. Also let us ship a complete, testable system before depending on model access.
**Consequences.** The "God agent" is currently choreography: it does not decide, adapt or re-plan. Results are still real (see the architecture doc §1). This is the main gap that v0.2 closes.

## ADR-004 · Deterministic tools for measurement, models only for judgement
**Status:** Accepted
**Context.** Judges may challenge numbers on a famous brand's site.
**Decision.** Speed, mobile and accessibility are measured by tools (browser metrics, CDP network totals, axe-core). Models are used only where judgement is needed (UX, AI-search clarity, design). Scores are computed by code from the evidence; the model never invents a score for the tool-based categories.
**Why.** Numbers must be reproducible and defensible, and every finding carries its evidence string.
**Consequences.** More code than asking a model to "audit this page", but the results hold up under questions.

## ADR-005 · Offline mode: every model-dependent step has a deterministic fallback
**Status:** Accepted
**Context.** No API key was available during the build, and a demo laptop might lose connectivity or hit a rate limit.
**Decision.** `llmText()` returns `null` when no key is set. Each caller then uses a rule-based path (UX heuristics, AI-search heuristics, template prototype). The UI header shows "Offline mode" or "Live model".
**Why.** The system always works end to end and the model upgrades quality instead of being a single point of failure.
**Consequences.** Offline scores for UX and AI-search are cruder and the prototype looks generic. The model paths are untested until a key is configured. Offline mode must be called out on stage if used.

## ADR-006 · Server-Sent Events (SSE), not WebSockets, for the live feed
**Status:** Accepted ("fine for now")
**Context.** The browser needs a live stream of events while a run progresses. Starting a run is one request; after that, data flows only from server to browser.
**Options.** (a) WebSockets; (b) SSE; (c) polling.
**Decision.** (b).
**Why SSE fits here.**
1. **Direction.** The feed is one-way (server → browser). WebSockets are two-way, and we do not use the second way. The one browser→server action (start a run) is an ordinary POST.
2. **Simplicity.** SSE is plain HTTP: the server writes `data: …\n\n` lines. No upgrade handshake, no extra library, no message framing or heartbeat code. The whole server side is about ten lines.
3. **Built-in reconnect.** The browser's `EventSource` reconnects by itself. Paired with our "replay history on connect" step, a dropped connection loses nothing visible.
4. **Works with normal tooling:** `curl`, browser dev tools, proxies and standard HTTP logging.
5. **Replayable:** the same event objects are saved to `trace.json`, so a later replay mode can reuse the same format.
**When WebSockets would be better.** If the browser must send frequent messages into a *running* agent (for example the agentic intake asking the user clarifying questions mid-run, interrupting, or steering). Even then, a POST for each user reply plus the SSE stream for output often suffices. We will revisit this in v0.2 if the intake conversation needs it.
**Consequences.** Browsers limit SSE connections per host (about six on HTTP/1.1), which is not an issue with one run per tab. Moving to WebSockets later only changes `server.ts` and the connection code in `index.html`; the `FeedEvent` shape stays the same.

## ADR-007 · Every tool and skill goes through `defineTool`, which posts to the feed
**Status:** Accepted
**Context.** The requirement: every skill or tool execution must show a fun post in the live feed.
**Decision.** One wrapper creates every tool. It requires a `feed` spec (start lines, end template, error line) and emits start/end/retry/error events automatically. A tool without a feed spec does not type-check.
**Why.** Coverage is guaranteed by the type system, not by each author remembering.
**Consequences.** All tool code follows one shape. End lines are filled from real results, so the jokes cannot lie about numbers. The planned CI lint rule is replaced by the compiler.

## ADR-008 · Speed from Playwright observers in v0.1.0; Lighthouse to be added
**Status:** Accepted for v0.1.0; **superseded by ADR-018** on the v0.2 branch (Lighthouse added, this path kept as fallback)
**Context.** The plan named Lighthouse; it is heavier to wire up.
**Decision.** v0.1.0 measures LCP and CLS with browser performance observers and totals bytes and requests through the DevTools protocol.
**Why.** Good enough to prove the pipeline, quick to build, and no extra dependency.
**Consequences.** No network or CPU throttling, so numbers are optimistic compared to Lighthouse's mobile profile. Lighthouse (local, mobile profile) is planned, keeping this path as the fallback.

## ADR-009 · Org match score: explainable formula over hardcoded skills
**Status:** Accepted
**Context.** Requirement: an organisation match score based on org skills, hardcoded for now.
**Decision.** `config/org-skills.json` holds 13 sample skills (level, headcount, available now, available-from date) behind an `OrgSkillProvider` interface. Needed skills come from fixed baselines plus the audit findings. Score = `100 × Σ(weight × fit) / Σ(weight)` with `fit = 0.6 × proficiency + 0.4 × depth`.
**Why.** Deterministic and explainable: the same inputs give the same score and each skill's contribution is visible. A model could propose skills but cannot change the arithmetic.
**Consequences.** The 0.6/0.4 split, the baseline skills and the needed level (4) are judgement calls and live as constants in `orgMatch.ts`. Scores are high for generic web work; variety requires more skill categories. The team and estimate use the separate synthetic bench in `config/bench.json`.

## ADR-010 · Shared run context in memory, with every event recorded
**Status:** Accepted
**Decision.** Each run has a `RunContext` (id, folder, event bus, data bag) held in a `Map`. Every event is appended to the bus and saved as `trace.json` at the end. Agents pass results through the context rather than calling each other.
**Why.** Simple, fast, and the trace doubles as the basis for a replay mode.
**Consequences.** Restarting the server loses in-memory runs (files stay). No persistence layer, no multi-user isolation.

## ADR-011 · Development workarounds for Chromium and `tsx`
**Status:** Accepted (technical debt)
**Context.** (1) The installed Playwright expected a Chromium revision that was not downloaded, while older revisions were cached. (2) Under `tsx`, esbuild injects a helper named `__name` into functions, which breaks functions sent into the page via `page.evaluate`.
**Decision.** (1) If the default launch fails, use the newest cached headless shell, or `CHROMIUM_PATH`. (2) Every browser context is created through `newContext()`, which stubs `window.__name`.
**Why.** Avoids a large browser download and keeps the dev loop working without changing the toolchain.
**Consequences.** A newer Playwright install (`npx playwright install chromium`) removes need for (1). (2) stays until the code is compiled with plain `tsc` or the helper is disabled.

## ADR-012 · Prototype is real HTML in a sandboxed iframe
**Status:** Accepted
**Decision.** The prototype is a self-contained HTML file served from the run folder and shown in an iframe with `sandbox="allow-popups"` (no scripts, no same-origin access). Offline mode uses a fixed template filled with the prospect's own content. With a key, a model generates the HTML, which is trusted less and therefore sandboxed.
**Why.** "Clickable and real" is the demo moment, and generated HTML must not be able to touch the app.
**Consequences.** Model-generated pages that need JavaScript will not run inside the sandbox. The mobile menu uses `<details>` to avoid scripts.

## ADR-013 · Release strategy: freeze v0.1.0 as the fallback; build the agentic version on a branch
**Date:** 2026-10-25 · **Status:** Accepted
**Context.** The user wants a proper working copy to fall back on in case the move to agents goes wrong. They also want everything explained and decisions logged.
**Decision.**
1. Commit the current state and **tag it `v0.1.0`** ("fixed pipeline, real results").
2. Do the agentic work (intake agent, planning lead, Agent SDK) on a **branch `v0.2-agentic`**, not on the main line.
3. Merge to `master` and tag `v0.2.0` only when the agentic version passes the same checks as v0.1.0 on a few brands.
4. Keep the fixed pipeline callable as a mode so the two can be compared on the same URL.
5. Every decision from here on gets an ADR entry in this file in the same commit that implements it.
**Why.** A tag is an immutable, always-runnable copy; a branch isolates risk. Falling back is one command: `git checkout v0.1.0`.
**Consequences.** Slight overhead of keeping two paths while v0.2 matures. Documentation must be updated alongside code.

## ADR-014 · SSRF protection limited to the entry URL (acceptable on a laptop)
**Status:** Accepted for local use; must be hardened before any hosting
**Decision.** The submitted URL is normalised and its DNS result is checked against private, loopback and link-local ranges. Redirect targets and page subrequests are not checked.
**Why.** The app runs on the presenter's laptop; full request interception is extra work with little demo value.
**Consequences.** A hosted deployment needs request-level filtering, DNS pinning and redirect checks.

## ADR-015 · PPTX through pptxgenjs; PDF deferred
**Status:** Accepted
**Decision.** The deck is generated as PPTX from run data only. PDF export is deferred.
**Why.** The CMO workflow edits PPTX; PDF is an easy later addition (print the same data to PDF).
**Consequences.** The deck layout is programmatic and plainer than a hand-designed template.

## ADR-016 · Testing scope reduced: prove it on a few brands, not 30
**Date:** 2026-10-25 · **Status:** Accepted (user decision)
**Context.** The release plan called for a 30-site regression set and nightly runs.
**Decision.** Test on a small handful of well-chosen brands (for example 3 to 5) that cover easy and harder sites, and rehearse the demo on those. The 30-site run is dropped.
**Why.** The goal is to prove the idea convincingly, not to guarantee coverage of every website.
**Consequences.** Unknown sites may fail on stage. Mitigations remain: pre-warm a few brands and keep a replay/fallback ready. The release plan's 30-site gates are superseded by this entry.

## ADR-017 · "Agentic flow" means the lead agent decides at runtime (no separate intake agent)
**Date:** 2026-10-25 · **Status:** Accepted (replaces the earlier "agentic intake" proposal)
**Context.** I first read "agentic intake flow" as a conversational intake agent. The user clarified that "intake" was a typo: they want an *agentic flow*, meaning the lead agent should make decisions instead of running a fixed script.
**Decision.** No separate intake agent. The input stays "a URL". The new behaviour is in the lead agent (see ADR-020). Free-text briefs and RFP intake remain possible later additions.
**Consequences.** The earlier idea of a two-way clarification conversation, and with it the case for WebSockets (ADR-006), is parked.

## ADR-018 · Lighthouse for speed, with the Playwright path kept as fallback
**Date:** 2026-10-25 · **Status:** Accepted (v0.2 branch)
**Context.** The Playwright timings in v0.1.0 are un-throttled and optimistic. Lighthouse is the standard that judges and clients recognise.
**Options.** (a) PageSpeed Insights API (Google's servers, needs a key and network); (b) Lighthouse locally; (c) keep Playwright only.
**Decision.** (b). `src/tools/lighthouse.ts` launches its own headless Chrome (via `chrome-launcher`, using the same executable resolution as Playwright), runs Lighthouse 12 with the performance category on the mobile profile and simulated throttling, with a 90 s timeout. The speed score is Lighthouse's own performance score. Findings use real Lighthouse numbers (LCP, TBT, CLS) plus its top "opportunities" with estimated savings. If Lighthouse fails or times out, a warning is posted to the feed and the old Playwright calculation is used. `NITRO_LIGHTHOUSE=0` disables it. The prototype re-audit does not use it (a local file would not be a fair comparison).
**Why.** Credible, recognisable numbers; works offline on the laptop; no new account or key.
**Consequences.** A run now takes about 30 s on a heavy site (Samsung India: Lighthouse mobile score 28, run 32 s) versus about 8 s before. Lighthouse is sensitive to CPU load and the other inspectors run at the same time, so scores can vary a little between runs. Lighthouse's headless Chrome is separate from the Playwright one, so two Chrome processes run at once.

## ADR-019 · Secrets from a git-ignored `.env`, loaded at startup
**Date:** 2026-10-25 · **Status:** Accepted
**Decision.** `src/core/env.ts` loads `./.env` with Node's built-in `process.loadEnvFile` before anything reads configuration; real environment variables take precedence. `.env` is git-ignored and `.env.example` documents the variables (`ANTHROPIC_API_KEY`, `NITRO_MODEL`, `NITRO_LEAD`, `NITRO_LIGHTHOUSE`, `CHROMIUM_PATH`, `PORT`). A malformed file is ignored and the app runs in offline mode.
**Why.** The key never passes through chat or source control, and no dependency is needed.
**Consequences.** Restart the server after editing `.env`. Without a key the header says "Offline mode".

## ADR-020 · Planner-driven lead agent with guardrails and a rule-based fallback
**Date:** 2026-10-25 · **Status:** Accepted (v0.2 branch). Model planner verified on two live runs (Allbirds, Stripe): it chose sensible orders and wrote the feed reasons; see ADR-022 for the live-test findings.
**Context.** The user wants an agentic flow: the lead should decide what happens next, not run a script.
**Options.** (a) Claude Agent SDK with the sub-agents as tools; (b) our own loop in which a *planner* picks the next step(s) and our code executes them.
**Decision.** (b). `src/agents/lead.ts` runs a loop: build a state summary (what is done or failed, attempt counts, audit facts, regressions), ask the planner for a decision (`run` some steps in parallel, or `finish`), post its reason to the feed, run the steps, record results, repeat. Two planners share one interface (`src/agents/planner.ts`):
- **RulePlanner** encodes the v0.1.0 flow as a policy (audit, then redesign and bench in parallel, then deck) plus one adaptive rule: if the re-audit shows a category got worse and a model is available, retry the redesign once with that feedback.
- **LlmPlanner** asks the model for a JSON decision. Its output is validated by hard guardrails: known steps only, prerequisites completed, no repeats beyond attempt limits (redesign may run twice, others once), a budget of 8 planning rounds, and no finishing early while buildable work remains. Any invalid, unparseable or failing response falls back to the rule planner for that round, and the feed says so. The run therefore always progresses.
`NITRO_LEAD=fixed` forces the rule planner. Without an API key the rule planner is used automatically, so offline behaviour is identical to v0.1.0.
**Why.** The model gets real decisions (order, parallelism, retries) while ordering safety and termination are enforced by code. It can be unit-tested without a key by injecting a scripted model. It avoids a new SDK and its tool-loop behaviours on stage.
**Consequences.** The set of decisions is deliberately small: the model chooses among four known steps. Adding steps (for example a deeper audit, a second design variant) increases what it can decide. Using the Agent SDK remains an option if we want open-ended tool use. The prompt and the model's decisions are not yet validated against the live API.

## ADR-021 · Unit tests for the planner and lead loop, using fake runners and a scripted model
**Date:** 2026-10-25 · **Status:** Accepted
**Decision.** `npm test` runs `src/test/planner.test.ts` (Node's built-in test runner via `tsx`): 8 tests cover the v0.1 sequence, a failed redesign skipping the deck, a fatal audit failure, a model choosing a different valid order, fallback on invalid / garbage / erroring model output, the early-finish guard, guardrails, and the regression retry rule.
**Why.** The agentic logic can be verified without an API key or a browser, in under a second.
**Consequences.** These tests verify the loop and guardrails, not the quality of the model's choices; that needs live runs.

## ADR-022 · Live model validation: findings and fixes
**Date:** 2026-10-25 · **Status:** Accepted
**Context.** With a key available, the model-dependent paths ran for the first time against real sites (allbirds.com twice, stripe.com once).
**What worked.** The model planner chose the right sequence and wrote natural one-line reasons; the vision UX review spotted real, specific problems (for example a blocking shipping modal hiding the hero on allbirds.com); the model-designed prototype was a clear step up from the template (on-brand, real imagery, accessible).
**What went wrong, and the fix.**
1. *Prototype generation silently fell back to the template and cost ~70 s.* The call was non-streaming with a large token limit and the failure was swallowed. Now: the call **streams**, the limit is 9000 tokens with a "compact page, about 250 lines" instruction, truncation is detected (`TruncatedError`) and unusable output is reported as a warning in the feed with the reason, then the template is used. While waiting, the lead's designer posts "still typing… about N lines" updates so the feed is never silent. Live result: about 40 s for the design step.
2. *A "regression" retry triggered on a meaningless difference.* AI-search was re-checked at page level against a site-level "before" score, so it looked like a drop, and the retry ran on the template where it could not help. Now: AI-search is **not** re-run on the prototype (robots.txt and llms.txt belong to the site), regressions only count for categories that dropped by 5 or more points, and a retry is only proposed when the prototype came from the model.
3. *UX before/after were not comparable* (vision model before, heuristics after). Now the same vision review runs on the prototype screenshot.
4. *Brand colour equal to the background* (allbirds: both #ece9e2). If the extracted primary equals the background, the text colour is used.
5. *Accessibility inspector failed on sites with a strict Content-Security-Policy* (stripe.com blocked injecting axe-core, and the retry wasted ~40 s). The audit browser context now sets `bypassCSP`. It is our own measurement browser; no site content is changed.
**Consequences.** Full runs take about 85 to 110 s with a model (audit ~35 s dominated by Lighthouse, design ~40 s). That is longer than the original 5-minute target allows for a comfortable live demo, so the feed's progress messages matter; shaving time (a faster model for the design step, or starting design earlier) is an open option. Offline runs remain about 30 s.

## ADR-023 · Replay mode is the default; every run saves a trace
**Date:** 2026-10-25 · **Status:** Accepted
**Context.** Looking at what happened in a past run must not cost model tokens, browser time or network. Until now only runs started from the web UI saved `trace.json`; the command-line runs (including the live Allbirds and Stripe tests) saved nothing, so they cannot be replayed.
**Decision.**
1. Every run, from the UI or the CLI, ends with `saveTrace(run)`, which writes all feed events (including the panel data that fills the audit, redesign, team and deck tabs) to `runs/<id>/trace.json`.
2. `GET /api/runs` lists saved runs from disk (title, score, duration, time), and `GET /api/replay/<id>/events?speed=N` streams a saved trace over SSE with the original timing scaled by `speed` (`0` = instant). Pauses longer than 2.5 s at 1x are shortened so a 70 s model call does not become a 70 s wait. These endpoints read files only.
3. The UI opens in **Replay** mode (remembered per browser): a run picker, a speed selector and a Replay button. **Live** mode is an explicit switch, labelled "Live runs use model tokens". So a casual click can never spend tokens.
4. `npm run replay -- list` and `npm run replay -- <id> [--fast]` print a saved run in the terminal, also reading the trace only.
**Why.** It answers "what happened in that run" for free, and doubles as the demo's fallback when the network or API fails on stage (replay needs neither).
**Consequences.** Replay shows what the agents *posted*; the artefacts (screenshots, prototype, deck) are served from the run folder, so deleting a folder breaks its replay. Runs made before this change without a trace are listed as "no saved trace"; their files can still be opened from `runs/<id>/`. A trace does not include the raw crawl, so a run cannot be re-analysed from it, only re-watched.

## ADR-024 · Technology detection and HAR-style traffic analysis, mapped to our org skills
**Date:** 2026-10-25 · **Status:** Accepted
**Context.** The user wants to see which technologies a prospect runs (frameworks, analytics, commerce and CMS platforms, Adobe, Salesforce, Hybris, .NET, Java, Python and so on), quick traffic statistics, and how each technology matches our skills.
**Decision.**
1. **Data source.** The crawl now records a HAR-style list of every request (URL, host, Chrome resource type, MIME, status, transferred bytes, first/third-party), the main document's response headers, first-party cookie *names* (never values), the page HTML (capped at 500 KB, used only for matching, not stored in the trace) and a probe of about 80 window globals (React, `dataLayer`, `_satellite`, `Shopify`, `Granite`...). This costs no extra page loads.
2. **Detection** (`src/core/techSignatures.ts`, a pure function). 87 signatures across 15 categories (132 across 17 since ADR-036): frontend frameworks, commerce platforms (SAP Commerce/Hybris, Salesforce Commerce Cloud, Magento, Shopify...), CMS (Adobe Experience Manager, WordPress, Drupal, Sitecore), marketing (Adobe Campaign, Salesforce Marketing Cloud/Pardot, Marketo...), analytics, tag managers, personalization, CDN and hosting, server and language (.NET, Java, Flask, Django, Python, Node, PHP), payments, consent, monitoring, search, support. A technology is **confirmed** with two or more independent signals (header, cookie, markup, request URL, global) and **likely** with one. Evidence is kept and shown on hover.
3. **Precision rules.** Server-language signals only count requests to the site's own domain (a third party's `.php` says nothing about the site), and only first-party cookies are used.
4. **Traffic stats** (`src/core/stack.ts`): weight and requests by type, third-party share, domains contacted, busiest domains, failed requests.
5. **Org coverage.** Each technology maps to an org skill (new sample skills added to `config/org-skills.json`: SAP Commerce, Salesforce Commerce and Marketing Cloud, AEM, Adobe Campaign, Adobe Analytics, .NET, Java, Python, Node, PHP, Magento, WordPress, Vue, Angular, analytics, personalization, payments). Status: **strong** (skilled and 2+ free), **partial**, **gap** (nobody free); coverage score = strong 1, partial 0.6, gap 0, averaged. The detected stack also feeds the organisation match score: platform technologies (commerce, CMS, marketing, server) weigh 0.7, the rest 0.4.
6. A new agent, the **Tech Detector**, runs in parallel with the five inspectors, posts large "headline number" tiles to the feed, and fills a new **Tech stack** tab.
**Why.** Passive signals from one page load give a credible, evidence-backed picture quickly, and tie the prospect's stack directly to our bench, which is the point of the pitch.
**Consequences.** Detection is a strong hint, not a certainty: back-end technologies are often hidden behind CDNs, and single-signal matches can be wrong (the UI marks them dashed). Only the homepage is examined. The sample org skills include deliberate gaps (Adobe Campaign, Shopify) so scores vary by prospect. Allbirds, for example, is detected as Shopify and shows our Shopify gap. Signature tables need occasional maintenance.

## ADR-025 · Feed UI: newest first, headline numbers, screenshots, plain agent names, light theme
**Date:** 2026-10-25 · **Status:** Accepted
**Decision.**
1. The feed shows the **newest post at the top**, like a timeline. A reader who scrolled down keeps their place when new posts arrive.
2. Events can carry a `stat` (a large animated number, for example "49% of requests are third-party") and an `image` (a screenshot). Screenshots of the homepage, the phone view and the prototype are posted as thumbnails that open full size on click.
3. Agents have **plain names that say what they do**: Coordinator, Site Auditor, Tech Detector, Speed Tester, Mobile Tester, Accessibility Checker, UX Reviewer, AI-Search Checker, Designer, Team Matcher, Deck Writer. Names come from `PERSONAS` and are looked up at display time, so old traces show the new names on the lanes (their message text keeps the older wording).
4. A **light theme** (now the default) and the dark theme share one set of CSS variables, with a toggle in the header.
**Consequences.** Old traces recorded before this change have no stats, images or Tech Detector posts; replay still works.

## ADR-026 · Slower replay pacing
**Date:** 2026-10-25 · **Status:** Accepted
**Decision.** Replay keeps each event visible for at least 450 ms at normal speed (previously bursts of events appeared at once) and the default speed is **Slow** (0.5x). Choices: Slow, Normal, Fast, Instant. Long gaps are still capped at 2.5 s at normal speed.
**Consequences.** A 55-event run takes roughly 1 to 2 minutes at the default speed.

## ADR-027 · Results as their own posts, one post per technology, no blinking, paced live feed
**Date:** 2026-10-25 · **Status:** Accepted (branch `v0.3-feed-polish`)
**Context.** Feedback on the first live runs: (1) a result such as "Speed Tester finished" appeared far down the feed, merged into the line where that tool had started, so it looked like nothing new had happened; (2) all detected technologies were squeezed into one headline number; (3) the headline-number tiles re-played their animation every time the feed redrew, which looked like blinking; (4) posts arrived too fast to read; (5) the model's page was cut off at the token limit and the design fell back to the template.
**Decision.**
1. **Result cards.** A tool or skill may define a `card` in its feed spec. When it finishes, the end event is posted as a **new, formatted card at the top of the feed**: title, grade badge, score out of 100, headline, and a small grid of key metrics, with the colour tone from the grade. The earlier "started" line stays where it was, dimmed with a tick. Used by the five inspectors, the Tech Detector and the organisation match. Tools without a card post a compact "done" line as a new post.
2. **One post per technology.** The Tech Detector posts each detected technology as its own card (name, category, confirmed or likely, first piece of evidence, and our team's coverage: strong, partial or gap), 0.7 s apart, after a "Spotted N technologies" tile.
3. **No blinking.** The feed is rendered **incrementally**: an existing post's element is only replaced if its content changed (for example a spinner becoming a tick). Entry animations apply only to newly added posts, and screenshots are no longer re-created on every update.
4. **Pacing.** Live posts go through a queue and are shown about every 0.8 s (faster if many pile up, so the feed never falls far behind). Replay keeps events at least 0.7 s apart at normal speed (1.4 s at the default Slow setting).
5. **Truncated designs.** The model's page budget is raised to 14000 tokens with a harder brief (at most 220 lines, about 70 lines of CSS). If the output is still cut off *after* its styles and some body content are complete, the page is **salvaged**: the broken last tag is dropped, the open tags are closed, and the feed says so. If the styles themselves are incomplete, the template is used, as before.
**Consequences.** More posts per run (cards plus a start line each); the feed is longer, but each item is readable. Live runs finish slightly later than the work itself because of display pacing. Older traces replay fine but have no cards: results show as compact lines. Salvaged pages may be missing their last section; the warning in the feed says when this happened.

## ADR-028 · Animated pixel office, pixel robot avatars, and a separate review window
**Date:** 2026-10-25 · **Status:** Accepted (branch `v0.3-feed-polish`)
**Context.** The right-hand report tabs (audit, tech stack, redesign, team, deck, ROI) were visible during the analysis, which made the screen cluttered while results were still arriving. The user wanted a gamified view of the agents working in an office, a distinct pixel robot for every agent, a visible "who is working" signal, and the review to open only when a human asks for it.
**Decision.**
1. **Pixel robots.** Each agent has a procedurally drawn 16x22 pixel robot (`web/sprites.js`: body colour, antenna, eyes, accessories), so no image files are needed. The same sprite is used as the portrait in the agent list and feed posts and as the character in the office, so they always match.
2. **The office** (`web/office.js`) replaces the report tabs on the main screen: a light, uncluttered pixel-art room with ten desks in two rows and a walking lane. Each robot sits at its desk, types while it has work in progress, and shows a small speech bubble (a tiny icon, deliberately not readable) that cycles between "thinking" and its own activity, then a green check, or a warning sign if something failed. The Coordinator wanders the lane; when any agent hands work to another (handoff, question, answer events), the sender **walks to the receiver's desk**, hands over a document, and walks back. When the run is done everyone cheers and confetti falls.
3. **Sync.** The office, the agent list and the feed are all driven by the same function (`show(event)`), called when a post is *displayed*, not when it is received. A live run (paced queue) and a replay therefore animate identically. Nothing in the office is random with respect to the run, apart from the Coordinator's idle wandering and blinking.
4. **Working indicator.** In the agent list, the portrait of every agent that is working blinks, and its name plate in the office turns accent-coloured. The list is updated in place, so the blink does not restart with every event. An agent counts as done once its results are posted.
5. **Review window.** When the run ends, the feed gets a quirky post from the Coordinator asking the human to start the review, with a **Start the review** button. The button opens `review.html?run=<id>` in a popup window containing the report tabs (audit, tech stack, redesign with before/after, team and match, deck, ROI). The review window reads the saved trace (`GET /api/runs/<id>/trace`), so it works for any saved run and costs nothing.
6. The shared parts moved out of the single page into `web/style.css`, `web/panels.js` (helpers, report panels, ROI, theme) and `web/review.html`.
**Why.** The analysis screen now shows only things that change in real time; the heavy report appears when a human is ready for it, and the whole thing is more fun to watch.
**Consequences.** The report tabs are no longer visible on the main screen, so the review window must be opened (popup blockers: the button is a user click, which browsers allow; if blocked it falls back to a new tab). The office is canvas art with a fixed light palette (dimmed in dark theme). Traces from before this change replay fine in the office, but have no tech-stack data in the review.

## ADR-029 · The Digithon presentation is an HTML page inside the app
**Date:** 2026-10-25 · **Status:** Accepted (branch `v0.3-presentation`)
**Context.** The user asked for a presentation explaining the whole project for the Digithon, in the same look as the app, with animations, starting from the organisation's pain points and building to the solution.
**Decision.** The deck is `web/presentation.html`, served by the app at `/presentation.html` (19 slides). It reuses the app's colour palette, the procedurally drawn pixel robots (`sprites.js`) and the animated office (`office.js`), so it matches the product exactly and the closing demo slide runs the real office scene with a scripted run. Narrative: three pain slides (idle bench cost, slow generic proposals, the client never sees what we'd do for them), a dark "what if" slide with a countdown that ends in a flash, shockwave and screen shake (the big bang), then the solution (paste a URL, the 11 agents, the flow, the audit, the tech stack, the redesign slider, the team match, the deck, the live office, the technology, trust, the business case, the roadmap and a close). Numbers on the audit, stack, redesign, match and ROI slides come from the real Allbirds run; pain-point baselines and ROI rates are labelled as assumptions. Navigation: arrow keys, space, click the screen edges, `F` fullscreen, `T` theme.
**Why not PPTX.** PowerPoint cannot show the live office, the countdown and bang, or the interactive before/after slider; the HTML page can, and it needs no extra tooling.
**Consequences.** It runs from the app (`npm start`, then `/presentation.html`), not as a standalone file; it needs a browser. Two Allbirds screenshots are stored in `web/assets/` (compressed). If a PowerPoint file is needed as well, the app already generates a 9-slide deck per run.

## ADR-030 · The product is renamed to Nitro
**Date:** 2026-10-26 · **Status:** Accepted (branch `v0.4-nitro`)
**Context.** "Pitch Agent" was already used by someone else. After several rounds of candidates, the name **Nitro** was chosen: it signals speed (the pitch in minutes, the bench off the mark) and is short enough to be a brand.
**Decision.** The product is called Nitro in the app header and page titles, the review window, the presentation, the README, the docs and `package.json` (`nitro`). Settings stored in the browser use `nitro-*` keys (so saved theme and mode reset once). The preview configuration is renamed `nitro`. Environment variables are now `NITRO_MODEL`, `NITRO_LEAD` and `NITRO_LIGHTHOUSE`; the old `PITCH_*` names are still honoured when the new ones are not set, so an existing `.env` keeps working. The generated customer-facing file is still called `pitch-deck.pptx` because it is a pitch deck, not the product.
**Not done.** No trademark or domain search has been done for "Nitro"; the word is common in software and very likely to be in use as a product or company name. Check before using it outside the hackathon. Old git tags and past decision-log text keep their original wording where it describes history.
**Consequences.** Documents written before this change that say "Pitch Agent" were updated in place, so older entries now say Nitro where they named the product.

## ADR-031 · Presentation content for AI evaluation, and an agent marketplace
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** The presentation will be judged partly by an AI, so it needs clear, keyword-rich content in plain language. The user asked for more pre-sales pain points, the effort saved, the role of our developers, full-stack insights, tests and journeys, LLM scores, HTML improvements, a RAG chat option, live-meeting use, 24x7 background agents, employee engagement, locale testing, and an agent marketplace built in the code.
**Decision.**
1. `web/presentation.html` grows from 19 to 31 slides in the same style: a pre-sales pain summary, full-stack insights (front end, back end, DevOps), agent-driven journeys and locale testing, outputs (LLM scores, HTML improvements, RAG chat, deck), agents plus experts, employee engagement through reviews, reaching CTOs in live meetings, 24x7 background agents, effort saved, the agent marketplace, who wins, and a one-slide recap. A `meta` description and keywords were added. Slide hooks now use slide ids instead of positions.
2. Every feature is labelled honestly: **today**, **beta** or **next**. Effort-saved figures (16 h manual vs 1 h review, 200 runs a week) and the locale score grid are labelled as assumptions or examples.
3. The **agent marketplace**: `config/marketplace.json` (23 agents: 11 live, 1 beta, 11 planned), validated by `src/core/marketplace.ts` (zod; ids unique; every running agent must be listed as live), served at `GET /api/marketplace` and shown at `/marketplace.html` with search and filters. The app header links to it, and the presentation's marketplace slide reads the same API.
**Consequences.** The catalogue must be kept up to date as agents are added; the test fails if a running agent is missing or marked as not live. Planned agents are descriptions only until built.

## ADR-032 · PowerPoint version of the presentation, and no more "bench"
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** The user needs the presentation as a .pptx file as well. They also asked us to stop using the word "bench": it reads as a negative label for people between projects.
**Decision.**
1. `scripts/build-pptx.mjs` (`npm run pptx`) builds `docs/Nitro-Digithon-2026.pptx` with pptxgenjs: the same 31 slides, numbers and colours as the HTML deck, with two slide layouts (dark and content), sections, speaker notes on every slide, native charts (audit scores, effort saved, score rings), alt text on every image and a slide listing the agent marketplace read from `config/marketplace.json`. The pixel robots, emoji icons and an office snapshot are pre-rendered PNGs in `web/assets/pptx/`, so the script needs only pptxgenjs.
2. In everything people read (both decks, the app, the review window, the marketplace, the feed lines, the README and the summary) "bench" is replaced by **available talent**, **available experts**, **developers between projects** and, for the cost, **unallocated capacity**. Internal names (`bench.ts`, the `bench` agent id, `config/bench.json`) stay, since nobody sees them and renaming them would break saved traces.
**Consequences.** The HTML deck and the .pptx are separate sources; a content change needs both (or a regenerated .pptx). Older entries in this log keep the word where they record history.

## ADR-035 · More pain points and a pain-to-answer slide, added on top of v0.4.0
**Date:** 2026-10-26 · **Status:** Accepted
**Context.** After the v0.4.0 presentation (ADR-031, ADR-032) was approved and merged, the user asked for more pain points: slow reach-out, no direction in reaching people, no contacts, slow demo build, demos that are not personalised, and skills not matched in the organisation. A parallel version of the deck with its own PowerPoint builder had been written; the v0.4.0 versions were kept as the base and only the new content was ported across.
**Decision.**
1. Three new pain slides in the web deck and the PowerPoint: **reaching out** (no contacts, no direction, slow reach-out), **demos** (slow to build, not personal) and **skills not matched** (no live view of who is available, deals chased blind, the right people wait). The problem section is now "1 of 6" to "6 of 6", followed by the existing "in short" summary.
2. A **"Pain → answer" slide** after "The pitch": eight pains, each with what Nitro does and a status (Today, Partly, Next). It says plainly that **contact finding and outreach drafts are not built** and that "no direction" is only partly answered, because the audit gives a concrete angle but not a full playbook.
3. Following ADR-032 and the v0.4.0 review, the new slides contain **no assumed figures** and say "available" rather than "bench".
4. One PowerPoint only: `docs/Nitro-Digithon-2026.pptx`, built by `npm run pptx` (`scripts/build-pptx.mjs`). The duplicate builder and file from the parallel version were removed. The deck now has 35 slides in both forms.
5. The saved runs folder (`runs/`) is tracked in git, so replays survive a lost laptop. The repository is private; the folder holds screenshots and concept redesigns of real brands.
**Consequences.** Two of the eight pains (contacts, outreach) remain open and are the first roadmap candidates. The `v0.3.1` tag on GitHub points at the pre-merge version of this work; the merged result is `v0.4.1`.

## ADR-033 · An 8-minute main track, token costs, and a replay you can follow at Fast
**Date:** 2026-10-26 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** The talk is 10 minutes: about 8 for slides and the rest for one replay. The deck had grown to over 40 slides. The problem had to land first (slow, expensive, generic proposals; we cannot target customers, so conversion is low), the cost of one analysis had to be shown, and a Fast replay was too quick to follow.
**Decision.**
1. **Main track of 11 slides**, then an Appendix divider and every earlier slide (kept for AI review): title; the pain points slamming in one by one with a screen shake; why conversion is low (a funnel); "What if"; paste a URL; how it works and what it identifies; the tech stack (real Allbirds run); stack to skills to people, with the project management system (PMS) integration marked as next; the report and estimate; what one analysis costs; impact, leading into the demo. The counter shows "3 / 11" in the main track and "Appendix n / m" after it; End jumps to the last main slide. The PowerPoint follows the same order: `build-pptx.mjs` now defines each slide as a named function, and the main track is a list of names.
2. **Token and cost tracking.** `llmText` takes `usage: { run, agent }` and posts a `usage` event with input, output and cache tokens and the list-price cost (`PRICES` in `llm.ts`; Claude Sonnet 5.5 at $2 / $10 per million tokens). The Coordinator posts the run total before `done`. Usage events are not shown in the feed. Runs saved earlier have no usage data.
3. **Dashboard.** The agent list shows each agent's avatar, a short description and the tokens (and cost) it used, or "tools only", and lifts like a card on hover; the panel header shows the run total. Major moments (tech stack mapped, site score, team matched, redesign built, pitch ready, run cost) pop up as a spotlight over the feed and then stay in a Highlights strip. During a replay, each spotlight holds the replay for 1.7 s, so a Fast replay can be followed. The holds apply to every saved run, because they are built from the panel events traces already contain.
**Consequences.** A Fast replay is about 9 s longer (5 to 6 holds). Cost figures are list prices; they change if the model or the prices change.

## ADR-034 · Click-driven builds, canvas transitions and a positive tagline
**Date:** 2026-10-26 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** Review of the main track: the tagline "We have great developers and no clients." ends on a negative; the pain slide shook and was too red; the conversion slide had too much on it (a funnel and four points); the "What if" slide ran on a timer; "The client never sees what we'd do for them" and "Meet the 11 agents" belonged in the main track; and plain slide-to-slide cuts felt traditional.
**Decision.**
1. Tagline: **"Great developers, in front of every client."** on the title and closing slides (both decks, README). Nitro is much larger on the title slide.
2. **Click-driven builds.** Any element with `data-frag="n"` appears on the nth click (right arrow, space, Enter or the right edge); after the last one the next click changes slide. Going back hides the last one first; returning to a slide shows it fully built. Used for the six pain points (they flip down one by one, no emojis, neutral cards, a calm "So conversion stays low."), the three reasons for low conversion (no targeting, no personalisation, no proof, with no funnel), and the "What if" slide, where the second click swaps the line and the third starts the countdown, the bang and the move to the next slide.
3. **Canvas transitions.** Each slide declares how it leaves with `data-out`: `up` and `right` pan the canvas, `flip` turns the slide away and the next one in, `zoom` scales into the element named by `data-zoom` (the email, the "Tech stack" tile, the estimate), and `fade`. Going back plays the move in reverse; jumps of more than one slide fade.
4. The main track is 13 slides: the client-never-sees slide follows the conversion slide, and Meet the 11 agents follows Paste a URL. The PowerPoint follows the same order (it has no builds or transitions).
**Consequences.** Presenting needs one click per build. The planning documents (01, 03) still quote the original hook as history.

## ADR-036 · Look longer, read more, and know more technologies
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** The user asked why samsung.com showed no Hybris, OneTrust, chat or Bazaarvoice. Probing samsung.com/in with the crawler's own settings showed the cause was mostly ours:
- *Hybris was on the page but unseen.* The markers (`Hybris-new`, `hybrisApiJson`, `<!-- new-hybris -->`) sit 880 KB and 1,065 KB into a 1.2 MB document, and only the first 500 KB of HTML was kept.
- *The crawl stopped too early.* At the moment it read the network the page had made 138 requests to 37 hosts; after scrolling and waiting it was 382 to 109. The chat widget, personalisation, feedback and most ad pixels load late.
- *Missing signatures.* Sprinklr chat, Insider, Medallia, Adobe Audience Manager, Bazaarvoice and the ad-tech cluster were unknown to us.
- *Some things were simply not there.* samsung.com/in loads no OneTrust (it has its own consent banner), and Bazaarvoice only loads on product pages. The UK buy page (`/uk/smartphones/galaxy-s26/buy/`) uses **TrustArc**, not OneTrust.
**Decision.**
1. **Dwell like a visitor.** After the screenshot, the crawler scrolls through the page in steps, moves the mouse and waits, for 10 seconds by default (`NITRO_DWELL_MS` overrides), then scrolls back to the top and reads the network log. Performance numbers and the screenshot are taken before this, so they are unaffected. A feed post says what it is doing. This adds about 10 seconds to a run.
2. **Keep more.** HTML kept for matching raised from 500 KB to 8 MB (the UK buy page alone is about 4 MB); the request log from 600 to 1,500 requests.
3. **45 new signatures** (132 in total, 17 categories): chat (Sprinklr, LivePerson, Genesys, LiveChat, Freshworks, Salesforce Service Cloud chat, Kore.ai, Yellow.ai, Haptik, Tidio), reviews and feedback (Bazaarvoice, Yotpo, Trustpilot, PowerReviews, Medallia, Qualtrics; a new category), personalisation (Insider, Salesforce Interaction Studio), Adobe (Audience Manager, Advertising Cloud, Web SDK), ad pixels (Microsoft Advertising, Snapchat, X, Amazon, Pinterest), more consent tools (TrustArc, Didomi, Osano, CookieYes, Quantcast), payments (Razorpay, PayU, Paytm, Worldpay, Checkout.com), search (Constructor, Klevu), analytics (Heap, Matomo), Imperva, reCAPTCHA, Google Maps, SAP Customer Data Cloud, and stronger Hybris API signals (`/occ/v2/`, `/rest/v2/`, `newhybris`). Programmatic ad exchanges and data partners are **one grouped entry**, not dozens of cards.
4. **More window globals probed** (Bazaarvoice `BV`, Insider, LivePerson, TrustArc, Didomi and others).
**Result on the same pages.** samsung.com/in: 11 technologies before, 25 now, including Hybris, Sprinklr, Insider, Medallia, Adobe Audience Manager and Microsoft Advertising. The UK buy page: Hybris (confirmed), Bazaarvoice, TrustArc, Java (JSESSIONID), Akamai and AEM.
**Consequences.** Runs are about 10 seconds longer. Detection is still passive, homepage-only (or whichever single URL is given), and each single-signal match is marked "likely". Bazaarvoice and similar tools will only appear when the URL is a page that uses them, for example a product page; crawling a second page automatically was not added. Five new unit tests cover the new vendors, the Hybris markers deep in a large page, grouped ad tech and the scrolling behaviour.

## ADR-037 · B2B wording, more of the story in the main track, a robot swipe and a slide tray
**Date:** 2026-10-26 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** Review: "We can't target customers" sounded like a legal restriction, and "no targeting / no personalisation" read like consumer e-commerce rather than B2B services. The demos pain needed a speed comparison; the redesign, the free developers and the CMO deck slides belonged in the main track; the impact slide was weak; the zoom after "What it generates" was dizzying; and there was no way to jump to a slide.
**Decision.**
1. Conversion slide: "We don't currently target customers, or show them anything specific to them." Points: we wait for RFPs; one pitch for every account; no proof before the deal.
2. Demos slide joins the main track with a comparison for one analysis of a prospect: days by hand during office hours, against 1.5 to 3 minutes per run with agents that can work 24x7.
3. Main track (17): title, pain points, conversion, client never sees, demos, What if, paste a URL, the agents, how it works, tech stack, redesign, free developers, stack to people, the report, cost, the CMO deck (now mini slides with real content), and the "Great developers, in front of every client" close. The impact slide moves to the appendix.
4. `data-out="swipe"`: a pixel robot walks across and wipes the next slide in (the old one is clipped away in step), used after "What it generates" instead of the zoom.
5. A slide tray (`G`, Esc, or the Slides button) lists every slide in the main track and the appendix; clicking one jumps there.
**Consequences.** The main track is longer (17 slides); the build steps keep each slide short to present. The PowerPoint follows the same order.

## ADR-038 · Review in a tab with a report switcher, a clearer Organisation match, an Estimate tab, and a Samsung SDS client deck
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** Feedback on the review and the deck: the Samsung report with the new crawler was not in replay (the earlier Samsung checks were crawler probes that were never saved as runs); the Organisation match screen was cramped; "Start the review" opened a separate window; the estimate was buried inside the team tab; and the client deck was plain, lacked detail, and had no Samsung SDS branding or a real intro.
**Decision.**
1. **Fresh Samsung reports saved.** Two full runs with the new crawler are in the replay list: samsung.com/uk Galaxy S26 buy page (46/100, 10 technologies including Hybris, Bazaarvoice and TrustArc) and samsung.com/in (60/100, 26 technologies).
2. **Organisation match tab, redesigned.** A large score ring with a strong/partial/gap count, a "where we are strong" card and a "gaps to cover" card (with availability), a skill-by-skill table (importance, our level, people free, fit bar, status) and matched-team cards with initials, skills, availability and fit.
3. **Estimate is its own tab.** The price range with a range bar, KPIs (person-days, weeks, people, blended day price, idle capacity put to work), an effort-by-workstream stacked bar, an indicative Gantt timeline, and the assumptions. The timeline is a simple picture of the effort, not a project plan.
4. **"Start the review" opens a normal browser tab** (named, so repeated clicks reuse it), not a popup window. The review page has a **report switcher** (dropdown of all saved reports; the selected tab stays selected so reports can be compared).
5. **Client deck rebuilt** (`src/agents/clientDeck.ts`, 17 slides): a Samsung SDS cover (Samsung blue, the Samsung SDS mark, the company name, today's homepage and the concept side by side), executive summary, scorecard, all findings with evidence and fix, technology review, how we cover their stack, before/after, phone view, what changed, organisation match, proposed team, effort and timeline, investment and assumptions, next steps, a closing slide and a method appendix. The company name is inferred from the domain and the page title (`src/core/brand.ts`), so it reads "Samsung UK" or "HDFC Bank" rather than a tagline. `npm run deck:rebuild -- <runId>` rebuilds a saved run's deck from its trace without re-running anything.
6. **Logo.** The deck draws a stand-in Samsung SDS wordmark in Samsung blue. The real logo is not in the repository (it is Samsung's trademark and was not available to the build); drop the official PNG at `assets/brand/samsung-sds-logo.png` and the deck uses it everywhere.
**Consequences.** The new deck could not be rendered to images here, so its layout was checked with a text-fit estimate (no overflow flagged) rather than by eye: open one in PowerPoint or Keynote before sending. Decks of older saved runs were regenerated in the new design. The Estimate timeline logic exists twice (browser and deck code) and must be kept in step.

## ADR-039 · Replay plays in the browser, so Stop and speed changes take effect at once
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** A replay was streamed from the server with its speed fixed when it started (ADR-023), so it could not be stopped or sped up part-way through.
**Decision.**
1. The page now fetches the saved run once (`GET /api/runs/<id>/trace`) and plays it back itself (`startReplay` in `web/index.html`). Nothing else changes about replay: no model, browser or network call, and the same feed, office and agent list react to each post.
2. **Stop.** While a replay runs, the Replay button is replaced by **■ Stop**. Stopping keeps what has been shown, stands the agents down (nobody is shown as mid-task, the lanes read "Stopped" and the office calms), and re-enables Replay. Switching to Live mode also stops a running replay.
3. **Speed, live.** The speed picker stays enabled during a replay: Very slow (0.25x), Slow, Normal, Fast, Faster (4x) and Instant. Changing it re-times the post that is already waiting, not only the later ones, so it applies immediately: slowing down stretches the current wait, speeding up shows an overdue post straight away, and **Instant** shows everything that is left at once. The choice is remembered.
4. The timing rules live in `web/replay.js` (no page code) and are unit-tested (`src/test/replay.test.ts`). A major moment still holds the replay for a beat (1.7 s) at every speed except Instant, so a fast replay stays followable; previously Instant held too.
**Consequences.** The server's `/api/replay/<id>/events` endpoint and `npm run replay` (terminal) are unchanged but the page no longer uses the endpoint. The 0.7 s and 2.5 s limits now exist in two places (server and `web/replay.js`) and must be kept in step. The whole trace is loaded into the browser, which is fine at current sizes (about 100 to 140 posts).

## ADR-040 · A calmer review dashboard, and logos for technologies
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** Feedback on the review: the Site audit should show the match score too (it is the most important screen); "How well we cover their stack" belonged at the top of the Tech stack tab; the screens had too much text in too small a size; busiest domains were too prominent; the Estimate tab was cluttered with colours. The user also asked for real logos for technologies, not emojis.
**Decision.**
1. **Site audit** opens with three large rings: **Site score**, **Organisation match** (highlighted) and **Stack coverage**. Below: a five-tile scorecard (score, grade, one key number each), the **three** things to fix first with a one-line impact (evidence and fix fold away), and an "All findings" list that is collapsed.
2. **Tech stack** opens with **How well we cover their stack** as the biggest number (with strong, partial and gap counts), then the number of technologies and the third-party share. Technologies follow as logo cards grouped by category with a single status dot. The coverage table comes next and the network traffic (page weight, busiest domains) is last, in a quieter style.
3. **Estimate** is the price range, three big numbers (weeks, person-days, people), a timeline and a sorted effort chart, all in the one accent colour (a grey bar for management). Assumptions are collapsed.
4. **Type and colour.** Review screens use a larger scale (16 px body, 44 to 100 px numbers), the system UI font stack (San Francisco on Mac), and one accent colour. Status colours appear only on small status dots and grade badges.
5. **Technology logos.** `config/tech-icons.json` maps 65 technologies to logos from the **Simple Icons** package (a dev dependency; the SVG files are CC0, but each brand remains its owner's trademark). `npm run icons` writes `web/assets/tech/<id>.svg`, a PNG of each for PowerPoint, and `icons.js` (the list). Technologies without a logo get a neutral monogram badge, not an emoji. Logos appear in the Tech stack tab, in the feed card for each detected technology, and on the client deck's technology slides. Any `web/assets/tech/<id>.svg` you add by hand is used too.
**Limits.** Simple Icons no longer carries several major brands at their owners' request (Adobe, Salesforce, Microsoft Azure, Amazon Web Services and others), so those show a monogram until you drop in the official file. About half of the 132 known technologies have a logo today. The server now sends SVG and JPEG with the right file types (SVGs did not display before).
**Consequences.** Review pages are denser vertically but quicker to read; the page needs `/web/assets/tech/icons.js`, which is generated. Logos are decoration, not evidence: detection still comes from requests, headers, cookies, markup and globals.

## ADR-041 · A landing screen: pipeline on the left, URL on the right
**Date:** 2026-10-26 · **Status:** Accepted (branch `claude/ppt-ai-evaluation-content-gxmf0y`)
**Context.** The app opened straight into the workspace (feed, office, replay). The user wanted a front door: the agents shown processing websites, the work already done, and a large, engaging place to enter a URL, as in the presentation.
**Decision.**
1. `/` is now a landing screen (`web/home.html`); the old page is the **workspace** at `/workspace.html` (the Nitro logo links back home).
2. **Vertical split.** The left 70% has a hero (logo, tagline and description), four stat cards (companies processed, decks prepared, agents running with the 11 pixel robots, websites in the pipeline) and a scrolling **"Agents at work"** list. The right 30% is **"Or enter a URL to analyse"** with the URL field and Analyse button, then "or replay" rows for the newest saved reports and a picker for all of them.
3. **The list** shows every real saved report (newest per website: Samsung India, Samsung UK, HDFC Bank, Allbirds...) with its score and **Review** and **Replay** buttons, mixed with **sample companies**: 50 hardcoded, clearly fictional names (`.example` domains) that move through the agents (waiting, audit, tech stack, design, team, deck) in real time, with a new one arriving every few seconds. Samples are labelled **Sample** and the header says so; the stat cards count them, with the real share stated under "Companies processed". The rules and names live in `web/pipeline.js` and are tested.
4. **Context hand-off.** Analyse opens `/workspace.html?mode=live&url=...&autostart=1`; a replay row opens `?mode=replay&run=<id>&autostart=1`. The workspace reads these, starts, and clears the address.
5. **Look.** Calm and pastel on request: white cards with a thin border, one accent colour, a pale tint for the hero, no gradients, normal-sized cards and a modest URL field. Every landing class is prefixed `h-` after an early clash with the workspace's `.lbl` and `.stat` styles (which had shown a dark pill and a hidden number).
6. In the workspace, the Office column is 10% narrower and the Live agent feed 12% wider, and feed posts are soft cards (hairline border, faint shadow, spacing between posts).
**Consequences.** The landing numbers mix real and sample work on purpose for the demo; they are not a record of real analyses. Pressing Analyse starts a live run and spends model tokens, as before.

---
## ADR-042 · RFP timing, a slower inbox, a clearer demos chart and a flip-through checks slide
**Date:** 2026-10-27 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** Review: the conversion slide repeated itself and missed the main point, which is the RFP; the email-to-inbox move was too fast and played on its own; the demos slide repeated "slow" and "not personal" and its chart did not say what it measured; the countdown before the big bang did not fit; and the "what it identifies" grid listed checks without showing any evidence.
**Decision.**
1. Conversion slide: "By the time an RFP reaches us, we are already late." A five-step buying timeline (problem noticed, research, shortlist, RFP issued, decision) marks where the deal is shaped and where we show up. Points: we arrive late; we look like everyone else; no proof before the deal.
2. "The client never sees" slide: the email pans away and lands in the inbox on a click, slowly; the move to the next slide is also on a click.
3. Demos slide: "Demos take days to build. Nitro builds one in minutes." The chart is labelled "Time to build one personalised demo for a prospect". Cards: every prospect gets one; always available, 24x7.
4. The countdown is removed; the big bang stays and moves to the next slide.
5. New "Eight checks, each with evidence" slide after "How it works": the checks are listed on the left and each click flips the panel on the right to that check's real Allbirds result (scores, screenshots, rule failures, the stack, third-party weight and the brand kit). The PPTX shows all eight as a grid with the two screenshots.
---

## ADR-043 · A Market Researcher first, a Tender Scout, approvals with Knox, your own deck, and agents over MCP
**Date:** 2026-10-27 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** The pitch should open with what is happening at the company, not with our capabilities. Government tenders are a source of work nobody watches. Reviewers need to approve each part of a report and hand it on for further approval, and to bring their own deck. Other teams want to reuse an agent without rebuilding it. Model calls are not available on the presenting laptop.
**Decision.**
1. **Market Researcher** (`src/agents/research.ts`, persona `research`) is the first step of a run, before the Coordinator's first planning round. Today it reads an imported brief (`config/research/*.json`, matched on the domain) instead of searching the web; the Nike brief is sample data and says so. `npm run research:add -- <runId>` puts the same posts into a saved run (idempotent; the shift is recorded on the opening post). The Nike run `mvpmet3q0sc1` now starts with it. In replay each signal pops up as a callout with "what we can do", then the brief as a summary that stays in the Highlights strip.
2. **Tender Scout** (`tenders`) is simulated on the home dashboard only: every third arrival is a government tender from a portal or RSS feed, shown with a government icon while it is triaged; a relevant tender goes on through the agents, the rest stop at triage as "Not relevant". It is beta in the marketplace and has no persona on the server.
3. **Review approvals**: every screen of the review has Approve and Request changes (with a note). **Submit Knox Approval** is enabled only when every screen with data is approved. State is kept in the browser per run; nothing is sent to Knox yet.
4. **Your own deck**: the Deck screen takes a .pptx upload (25 MB limit, stored under `runs/<id>/uploads/`, git-ignored) and checks its slide text against the analysis: research signals, site and category scores, technologies, redesign, team and estimate, with the slides where each appears and what to add. Plain text matching, no model.
5. **Marketplace**: a list like the home dashboard, with Active (and on what) or Idle per agent, from the dashboard when it is open, live runs on the server, or the same simulated pipeline. **Connect** shows how to reuse an agent over MCP: `/mcp` (or `/mcp?agent=<id>`) is a JSON-RPC endpoint with read-only tools on saved runs, plus `tenders_triage`; requests from other web origins are refused.
**Consequences.** 13 agents (12 in a run, 1 finding tenders), 25 in the marketplace (12 live, 2 beta, 11 planned), 49 tests. The research content and tender rows are demo data until a web-search step and real tender feeds replace them. The MCP tools never start a browser or spend tokens.
---

## ADR-044 · Guardrails for review against the Digithon criteria
**Date:** 2026-10-27 · **Status:** Proposed (branch `claude/ppt-ai-evaluation-content-gxmf0y`, for review)
**Context.** Review against the round 2 criteria (technical execution, agent design, business relevance, security and guardrails, product maturity) found gaps: website text went into prompts without an untrusted-data boundary; only the start URL was checked against private networks; model-written HTML could carry scripts; the agents did not hand decisions to a person with reasons; there was no CI; the README was not complete.
**Decision.**
1. `src/core/guard.ts`: website text reaches the model only inside `<untrusted>` tags under a system rule; phrases aimed at an AI are detected in the audit; model scores are clamped; model HTML is sanitised.
2. `src/core/ssrf.ts` `isAllowedRequest`, installed for every browser context: redirects and subrequests cannot reach private or internal addresses; only `GET /runs/` on this app is allowed locally. Run pages are served with a script-blocking CSP.
3. `src/core/policy.ts` `NEVER_ALONE`, posted at the start of each run; `escalations` in `lead.ts` hands a person the decisions the agents may not take alone, each with a reason, shown in the feed and above the review.
4. `/api/health`, clearer errors for ambiguous input, GitHub Actions CI (typecheck, tests, secret scan), `SECURITY.md`, and a README with full documentation and an evidence map per criterion.
**Consequences.** 56 tests. Route interception disables the browser HTTP cache during a crawl (each context starts empty anyway). Lighthouse's own Chrome is outside the request guard and documented as a gap.
---

## Superseded notes
- The release plan's CI rule "fail if a tool has no feed spec" is replaced by the compiler check (ADR-007).
- The release plan's 30-site regression gates are superseded by ADR-016.
