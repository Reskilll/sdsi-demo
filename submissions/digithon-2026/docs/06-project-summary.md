# 06 · Project summary (as of v0.2.1)

Nitro turns a prospect's website URL into a send-ready pitch: an audit, a technology-stack analysis, a redesigned homepage, a matched team of our available experts, and a deck plus proposal. A human reviews before anything is sent.

Releases: `v0.1.0` (fixed pipeline, the fallback), `v0.2.0` (planner-driven lead, Lighthouse, replay, tech stack), `v0.2.1` (result cards, pixel office, robot avatars, review window). Restore any with `git checkout <tag>`.

## 1. By the numbers

| | |
|---|---|
| **Agents** | **11** |
| **Skills** (model- or tool-backed capabilities, each posting to the live feed) | **11** |
| **Tools** (plain helpers, also posting to the feed) | **3** |
| Planner steps the lead agent chooses between | 4 (audit, redesign, bench, deck) |
| Technology signatures | 132, across 17 categories |
| Org skills (hardcoded sample) / sample developers | 31 / 18 |
| Automated tests | 38 (planner, tool wrapper, salvage, tech detection, marketplace, token cost) |
| Agent marketplace | 23 agents listed (11 live, 1 beta, 11 planned), at `/marketplace.html` |
| Decision-log entries | 41 (ADR-001 to ADR-041) |
| Code | about 3,700 lines of TypeScript, JavaScript, HTML and CSS |

## 2. The 11 agents

| Agent | What it does |
|---|---|
| Coordinator | The lead. Plans the job, picks the next step (rule-based offline, model-chosen with a key), hands work over, retries a regressed design once. |
| Site Auditor | Opens the site, takes the snapshot, runs the inspectors, builds the report card. |
| Tech Detector | Reads the page's network traffic and detects technologies; maps them to our skills. |
| Speed Tester | Lighthouse (mobile profile), with a Playwright timing fallback. |
| Mobile Tester | Reloads the page at phone size: viewport, overflow, tap targets, text size, screenshot. |
| Accessibility Checker | axe-core run in the browser. |
| UX Reviewer | Vision-model review of a screenshot against a rubric (rule-based fallback offline). |
| AI-Search Checker | Structured data, `llms.txt`, AI-crawler rules, answerability. |
| Designer | Extracts the brand kit and builds the new homepage (model-designed, template fallback), then has it re-audited. |
| Team Matcher | Organisation match score, matches available developers, estimates effort and price. |
| Deck Writer | Builds the 9-slide PPTX deck and the markdown proposal. |

## 3. Skills and tools

**Skills (11):** `skill.speed`, `skill.mobile`, `skill.a11y`, `skill.ux`, `skill.geo`, `skill.tech`, `skill.brand-kit`, `skill.prototype`, `skill.org-match`, `skill.team-match`, `skill.deck`.
**Tools (3):** `browser.render` (the crawl), `browser.screenshot` (prototype snapshot), `roster.load`.

Every one is created through `defineTool`, which posts a start line and a result (as a card when it defines one) to the live feed; a tool without a feed spec does not compile.

## 4. Tech stack

| Layer | Used |
|---|---|
| Language and runtime | TypeScript on Node.js 20, run with `tsx` |
| Server | Plain Node `http` server; Server-Sent Events for the live feed and replay |
| Browser automation | Playwright (headless Chromium) |
| Measurement | Lighthouse 12 (speed), axe-core (accessibility), Chrome DevTools Protocol (network log) |
| Model | Anthropic Messages API (`@anthropic-ai/sdk`), `claude-sonnet-5-5`, streaming; used for the planner, UX review, AI-search judgement and design |
| Documents | pptxgenjs (PPTX deck), markdown proposal |
| Validation | zod is installed; guardrails are in code (`planner.ts`) |
| UI | Vanilla HTML, CSS and JavaScript; canvas pixel art (procedural sprites and office); no framework or build step |
| Tests | Node's built-in test runner via `tsx` |
| Storage | Files only: `runs/<id>/` (screenshots, prototype, deck, proposal, `trace.json`) |

## 5. How a run works

1. Paste a URL. The server checks it is a public address, then starts a run.
2. The Coordinator asks the planner for the next step: audit first.
3. Site Auditor crawls (rendered page, request log, headers, cookies, markup) and runs five inspectors plus the Tech Detector in parallel. Result cards, screenshots and headline numbers stream to the feed.
4. Designer and Team Matcher run in parallel. The design is re-audited (accessibility, mobile, UX); a real regression triggers one retry.
5. Deck Writer builds the deck and proposal.
6. The Coordinator posts a request for a human; **Start the review** opens the report in its own window.
7. Everything is saved, so any run can be replayed for free at Slow, Normal, Fast or Instant speed.

## 6. What is real and what is sample data

Real: every measurement, finding, technology detection, brand kit, redesign and the re-audit. Sample or assumed: the org skills, the talent roster, the pricing constants (margin, days per issue), the ROI defaults, and the feed's jokes. See `04-architecture.md` §1.

## 7. Verified so far

Live runs with the model on allbirds.com (twice) and stripe.com; a Samsung India run; unit tests; replay in the browser. Live on the final build (v0.2.1): **not yet**.

## 8. Pending

| Item | Note |
|---|---|
| **Live verification of v0.2.1** (kept pending) | Run a fresh live run and check the office, result cards, per-technology posts, pacing and the review window together. |
| Run time | A full live run takes about 85 to 160 s (Lighthouse about 25 s, each design pass about 40 s, one retry adds a pass). |
| Salvage of cut-off designs | Unit-tested only; not yet seen against a real cut-off. |
| Review popup | Works in the app pane as a same-tab navigation; confirm it opens as a popup in a normal browser. |
| Deck appearance | Slide text was checked; the deck has not been opened in PowerPoint. |
| Dark theme | Built, not visually checked. |
| Missing traces | The earliest live tests (Allbirds, Stripe from the command line) saved no trace, so they cannot be replayed. |
| Real data | Talent roster, org skills and ROI inputs are samples; real data needs an HR or resource-planning adapter. |
| Not built | PDF export, RFP intake, CRM or send workflow, win/loss learning loop. |
| Optional | Move the lead to the Claude Agent SDK for open-ended tool use (ADR-003, ADR-020). |
