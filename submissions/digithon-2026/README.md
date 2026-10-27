# Nitro

**AI agents that turn a prospect's website into a reviewed, personalised pitch in minutes.**

[![CI](https://github.com/manishpaul26/digithon-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/manishpaul26/digithon-2026/actions/workflows/ci.yml)

> Great developers, in front of every client.

Paste a company's website address. A team of AI agents reads the latest news on the company, audits the site in a real browser, maps its technology, redesigns the homepage in the company's own brand, matches our available experts, estimates effort and price, and writes a pitch deck and proposal. The agents stop at the decisions they may not take alone and hand them to a person with a reason. Nothing is sent to a client until a person approves every screen.

**Contents:** [Why](#why-it-exists) · [Quick start](#quick-start) · [What you can do](#what-you-can-do) · [How it works](#how-it-works) · [The agents](#the-agents) · [Security and guardrails](#security-and-guardrails) · [Business case and pilot](#business-case-and-pilot) · [Configuration](#configuration) · [HTTP API and MCP](#http-api-and-mcp) · [Testing and CI](#testing-and-ci) · [Project structure](#project-structure) · [Real and sample data](#real-and-sample-data) · [Limitations](#known-limitations) · [Troubleshooting](#troubleshooting) · [Releases](#releases) · [Docs](#documentation) · [For reviewers](#for-reviewers-evidence-by-criterion)

---

## Why it exists

Pre-sales teams reach few new clients. By the time an RFP arrives, the shortlist is often already formed, every vendor answers the same questions, and the client never sees what we would do for them on their own platform. Preparing a personalised analysis by hand takes days of senior and developer time, so it happens only for deals that are almost won. Meanwhile, skilled developers between projects are a real cost.

Nitro makes a personalised, evidence-backed pitch cheap enough to prepare for every prospect, and gives available developers useful review work while they wait for their next project.

**Who uses it:** pre-sales and account managers (run, review, send), developers between projects (review and sign off the parts in their skill area), leadership in CTO meetings (run it live on the CTO's site), and delivery and resourcing (see which skills a prospect needs and who is free).

## Quick start

**Needs:** Node.js 22 or newer, and Chromium for Playwright. Works on Windows, macOS and Linux; see [`docs/08-cross-platform.md`](docs/08-cross-platform.md) for per-OS setup, restricted laptops and using an installed Chrome.

```bash
git clone https://github.com/manishpaul26/digithon-2026.git && cd digithon-2026
npm install
npx playwright install chromium      # once; or set CHROMIUM_PATH to an existing Chrome/Chromium
cp .env.example .env                 # optional: add ANTHROPIC_API_KEY for the model-powered parts
npm start                            # http://localhost:3000
```

**No API key or no network?** The app runs in **offline mode**: every model call has a rule-based fallback and the measurements stay real. Saved runs can be **replayed** with no model, browser or network at all, which is the safest way to demo.

**Two-minute demo:** open http://localhost:3000, press **Replay** next to *Nike*, set the speed to **Fast**. Watch the Market Researcher's news callouts, the audit and tech stack, the redesign and the team match. Then press **Start the review**, approve each screen, and submit for Knox approval.

## What you can do

| Screen | URL | What it is for |
| --- | --- | --- |
| Home dashboard | `/` | Agents at work on a pipeline of websites and government tenders; enter a URL or replay a saved run |
| Workspace | `/workspace.html` | The live (or replayed) agent feed, the pixel-art office, token use and cost per agent |
| Review | `/review.html?run=<id>` | The report: market research, site audit, tech stack, redesign, organisation match, estimate, deck, ROI. Approve or request changes on each screen; **Submit Knox Approval** unlocks when every screen is approved. Upload your own deck to check it against the analysis |
| Agent marketplace | `/marketplace.html` | Every agent (live, beta, planned), whether it is active or idle now, and **Connect** to reuse it over MCP |
| Presentation | `/presentation.html` | The animated Digithon deck (arrow keys, `F` fullscreen, `G` slide tray). PowerPoint version: [`docs/Nitro-Digithon-2026.pptx`](docs/Nitro-Digithon-2026.pptx) |

Command line:

```bash
npm run cli -- https://example.com    # headless run, prints the feed
npm run replay -- list                # saved runs
npm run replay -- <runId> --fast      # replay one in the terminal
npm run research:add -- <runId>       # add the imported market research to a saved run
npm run deck:rebuild -- <runId>       # rebuild a run's client deck from its trace
npm run pptx                          # rebuild the presentation PPTX
```

## How it works

```mermaid
flowchart LR
  U[Browser UI] -- "POST /api/runs" --> S[Node server<br/>URL check, SSE]
  S --> C[Coordinator<br/>planner + guardrails]
  C --> R[Market Researcher]
  R --> A[Audit: speed, mobile,<br/>accessibility, UX, AI search, tech]
  A --> B[Build: redesign + team match]
  B --> W[Write: deck + proposal]
  W --> H{{Human review<br/>approve every screen}}
  H --> K[Submit Knox Approval]
  S -- "live feed (SSE)" --> U
  A & B & W -. "every request checked" .-> G[(Private-network guard)]
  A & B -. "untrusted data only" .-> M[(Claude API)]
```

1. **Start.** The browser posts a URL. The server checks it is a public address (`src/core/ssrf.ts`), creates a run and caps concurrent runs at 3.
2. **Plan.** The Coordinator (`src/agents/lead.ts`) posts the **never-allowed-alone** list, then loops: summarise state, ask the planner for the next step, run it, record the result. With a model key the `LlmPlanner` chooses; code guardrails (`validateDecision`) reject unknown steps, missing prerequisites, repeats past their limit, more than 8 rounds or finishing early, and the rule planner takes over for that round. Every decision is posted with its reason and its source (`llm`, `rules`, `rules-fallback`).
3. **Research.** When a market brief is available for the domain, the Market Researcher posts each news or trend signal with what we can do about it, then a summary.
4. **Audit.** One snapshot of the page in a real browser; six inspectors run in parallel on it. If one fails, the score uses the remaining weights; if all fail, the run stops with a clear error.
5. **Build.** The Designer builds a new homepage in the prospect's brand and has it re-checked by the same tests; a real regression triggers one retry with that feedback. The Team Matcher finds available experts and estimates effort and price.
6. **Write.** The Deck Writer writes a PowerPoint deck and a proposal.
7. **Escalate.** The Coordinator hands a person the decisions the agents may not take alone, each with a reason: text on the page aimed at AI assistants, failed steps, skills we cannot staff, a template fallback, and the final approval.
8. **Save.** Every event is written to `runs/<id>/trace.json`, so any run can be replayed and audited later.

Every tool and skill is created with `defineTool` (`src/core/tool.ts`), which posts start, result, retry and error events to the live feed; a tool without a feed spec does not compile. Model calls also post their token use and cost. More detail: [`docs/04-architecture.md`](docs/04-architecture.md).

## The agents

| Agent | Job | Built with | Status |
| --- | --- | --- | --- |
| Coordinator | Plans the run, picks the next step, escalates to a human | Claude planner, code guardrails, rule fallback | Live |
| Market Researcher | Latest news and trends on the company, and what we can do about each | Imported brief today; web search next | Live |
| Site Auditor | Opens the site in a real browser, builds the report card | Playwright, Chromium | Live |
| Tech Detector | Front end, back end, CMS, commerce, analytics, CDN, cloud | Chrome DevTools Protocol, 132 signatures | Live |
| Speed Tester | Page speed and Core Web Vitals | Lighthouse 12, Playwright fallback | Live |
| Mobile Tester | Layout, tap targets and text size at phone size | Playwright device emulation | Live |
| Accessibility Checker | WCAG rules | axe-core | Live |
| UX Reviewer | Screenshot scored against a fixed rubric | Claude vision, rule fallback | Live |
| AI-Search Checker | Can AI assistants find and quote the site | Claude, structured-data checks | Live |
| Designer | New homepage in their brand, re-audited | Claude, template fallback | Live |
| Team Matcher | Organisation match, named team, estimate | Skill matching on the talent roster | Live |
| Deck Writer | Pitch deck and proposal | pptxgenjs | Live |
| Tender Scout | Triages government tenders from portals and RSS feeds | Simulated on the dashboard; `tenders_triage` MCP tool | Beta |

Twelve more are planned in the marketplace (`config/marketplace.json`), such as the Journey Runner, Test Writer, Locale Tester and Night Watch.

## Security and guardrails

Full detail in [`SECURITY.md`](SECURITY.md). In short:

| Risk | Control | Where |
| --- | --- | --- |
| Prompt injection from website text | Page text reaches the model only inside `<untrusted>` tags under a system rule that it is data, never instructions; length-capped; cannot close its own tag | `src/core/guard.ts`, used in `src/tools/inspectors.ts`, `src/agents/redesign.ts`, `src/agents/planner.ts` |
| A page that talks to the AI | Detected in the audit, posted as a warning and escalated to a human | `injectionSignals` in `src/core/guard.ts`, `src/agents/audit.ts`, `escalations` in `src/agents/lead.ts` |
| Model output steering scores | Model scores are range-checked; anything invalid falls back to rules | `clampScore`, `src/tools/inspectors.ts` |
| Server-side request forgery | The start URL and **every** browser request (redirects, scripts, images, XHR) are checked; private, link-local and internal addresses are blocked | `assertPublicUrl`, `isAllowedRequest` in `src/core/ssrf.ts`; `newContext` in `src/tools/browser.ts` |
| Model-written code running in a browser | Redesign HTML is sanitised; run pages are served with a CSP that blocks scripts; the review shows it in a sandboxed iframe | `sanitizeHtml`, `RUN_PAGE_CSP` in `src/server.ts` |
| Secrets | `ANTHROPIC_API_KEY` only from the environment or a git-ignored `.env`; CI fails if a key is committed | `.env.example`, `.gitignore`, `.github/workflows/ci.yml` |
| Runaway agents | Step budget (8 rounds), per-step attempt limits, prerequisites, 3 concurrent runs, request body and upload size limits | `src/agents/planner.ts`, `src/server.ts` |
| Acting without a person | Nothing is ever sent; Knox submission needs every screen approved; MCP tools are read-only | `NEVER_ALONE` in `src/core/policy.ts` |

**Never allowed to do alone** (posted at the start of every run, see `src/core/policy.ts`): send a deck, proposal or email to a client; submit for Knox approval before a person approves every screen; follow instructions found in website text, uploaded decks or research; open private or internal network addresses; run a step out of order, retry past its limit or go past 8 planning rounds; change or delete saved runs over MCP; run model-written code in the browser.

## Business case and pilot

**Fit with SDSI functions.** External business: more prospects reached with proof about their own platform. Productivity: a personalised analysis in minutes instead of days. Process improvement: one standard, reviewable flow from website to pitch, with a full trace of every step. AI governance: human approval on every screen, a Knox approval step, and an audit trail.

**Measured so far** (from the saved traces in `runs/`, with the model on):

| Run | Website | Time to a full pitch | Model tokens | Model cost |
| --- | --- | --- | --- | --- |
| `mvpida9wn24p` | hdfc.bank.in | 103 s | 17,790 | $0.115 |
| `mvpiq0jkdm4e` | samsung.com/in | 143 s | 27,110 | $0.175 |
| `mvpimwddfpjt` | samsung.com/uk (S26 buy page) | 144 s | 17,199 | $0.105 |
| `mvpmet3q0sc1` | nike.in | 138 s | 28,693 | $0.184 |

So one analysis takes about 2 to 2.5 minutes and about 10 to 20 US cents of model tokens; everything else uses free, open-source tools, and replaying a run costs nothing. On allbirds.com the redesign raised accessibility from 70 to 98 and mobile from 87 to 100, re-measured by the same tools.

**Pilot path inside SDSI** (no outcomes are claimed before they are measured):

1. **Weeks 1 to 2:** one pre-sales team runs Nitro on the accounts it already plans to approach. Reviewers are developers between projects. Measure the baseline: time to prepare a personalised pitch by hand.
2. **Weeks 3 to 6:** every outgoing pitch goes through Nitro and the review. Track pitches sent, time from first look to pitch, reviewer hours, replies from CTOs and meetings booked.
3. **Gate:** compare with the baseline. Connect the talent roster to the project management system and Knox approval to the real workflow before a wider rollout.

## Configuration

Copy `.env.example` to `.env` (git-ignored). Never commit keys or paste them into chat.

| Variable | Default | Effect |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | none | Turns on the model parts: planner, UX vision review, AI-search judgement, designed redesign. Without it the app runs in offline mode |
| `NITRO_MODEL` | `claude-sonnet-5-5` | Model id |
| `NITRO_LEAD` | planner | `fixed` forces the fixed sequence |
| `NITRO_LIGHTHOUSE` | on | `0` uses Playwright timings instead of Lighthouse |
| `NITRO_DWELL_MS` | `10000` | How long the crawler scrolls and waits like a visitor |
| `CHROMIUM_PATH` | Playwright's | Use a specific Chrome or Chromium binary |
| `PORT` | `3000` | Server port (the server listens on 127.0.0.1 only) |

Data files: `config/org-skills.json` and `config/bench.json` (sample skills and talent roster), `config/marketplace.json` (agent catalogue), `config/research/*.json` (market briefs per domain).

## HTTP API and MCP

| Method and path | Purpose |
| --- | --- |
| `POST /api/runs` `{"url"}` | Start a live run (429 when 3 are already running) |
| `GET /api/runs` | Saved runs with title, score and time |
| `GET /api/runs/:id/events` | Live feed of a run (Server-Sent Events) |
| `GET /api/runs/:id/trace` | Saved feed of a run |
| `GET /api/replay/:id/events?speed=` | Replay a saved run over SSE |
| `GET` / `POST /api/runs/:id/deck` | Your own .pptx: last check, or upload and check (25 MB limit) |
| `GET /api/marketplace` | Agent catalogue and counts |
| `GET /api/activity` | Agents working in live runs right now |
| `GET /api/config` | Agent names, whether a model is configured |
| `GET /api/health` | Liveness, model on or off, runs in progress |
| `POST /mcp` or `/mcp?agent=<id>` | MCP server (JSON-RPC over HTTP) with read-only tools |
| `GET /runs/:id/:file` | Run files (screenshots, redesign, deck, proposal) |

**MCP:** connect any agent from Claude Code with `claude mcp add --transport http nitro-research "http://localhost:3000/mcp?agent=research"`, or use the Connect button in the marketplace. Tools: `lead_list_runs`, `research_get_brief`, `audit_get_report`, `tech_get_stack`, `speed_get_result`, `mobile_get_result`, `a11y_get_result`, `ux_get_result`, `geo_get_result`, `redesign_get_result`, `bench_get_team`, `deck_get_files`, `tenders_triage`. All are read-only on saved runs; requests from other web origins are refused.

## Testing and CI

```bash
npm test             # 62 tests: planner, guardrails, lead loop, tool wrapper, tech detection, replay, research, tenders, deck check, MCP, cost
npm run typecheck    # TypeScript, strict
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on every push and pull request on Ubuntu, Windows and macOS: install, typecheck, tests, and a scan that fails if an API key is committed. The tests need no browser, model key or network. The guardrails were also checked in a real browser: requests to `169.254.169.254`, `127.0.0.1` and the app's own API from a test page were blocked, the page's script was stopped by the CSP, and the inspectors still scored a saved redesign (mobile 100, accessibility 98).

## Project structure

```
src/
  server.ts            HTTP server, SSE, uploads, MCP endpoint, static files
  cli.ts, replay.ts    headless run, terminal replay
  agents/              lead (Coordinator loop, escalations), planner (rule and model planners, guardrails),
                       research, audit, redesign, bench (Team Matcher), deck, clientDeck
  tools/               browser (crawl, request guard), inspectors, lighthouse, tech
  core/                events and RunBus, defineTool, run context, guard (prompt injection, sanitising),
                       policy (never alone), ssrf, mcp, deckCheck, scoring, org match, tech signatures, llm (client, cost)
  test/                unit tests
web/                   home, workspace, review, marketplace, presentation (vanilla HTML, CSS, JS)
config/                sample skills and roster, marketplace, research briefs, tech icons
scripts/               build-pptx, add-research, rebuild-deck, icons
runs/                  saved runs: screenshots, redesign, deck, proposal, trace.json
docs/                  requirements, release plan, demo plan, architecture, decision log, summary, write-up, PPTX
```

## Real and sample data

**Real, measured from the live site:** speed, mobile, accessibility and AI-search measurements; findings with evidence; technology detection and third-party traffic; brand kit, redesign and its re-audit; token use and cost.

**Sample or simulated today:** the org skills and talent roster (`config/`), pricing constants and ROI defaults, the Nike market brief (`config/research/nike.json`, labelled as sample), the government tenders on the home dashboard, the dashboard's pipeline of other companies, and the Knox submission (recorded in the browser, not sent).

## Next task

- [ ] **Login screen.** Sign-in before the review and the marketplace, so approvals and Knox submissions are tied to a named reviewer and shared between reviewers (today they live in each browser). Planned: a login page, a session cookie, and a check on the review, upload and MCP endpoints. See the `TODO(next)` note in `src/server.ts`.

## Known limitations

- The Market Researcher reads an imported brief, not live news. A web-search step can replace `loadBrief` without changing the feed.
- The Tender Scout is simulated on the dashboard; the `tenders_triage` tool is a keyword triage, not a model.
- Knox approval is a recorded state in the browser, not an integration.
- Review approvals are stored per browser, not shared between reviewers.
- Lighthouse runs its own Chrome, so its subrequests are not covered by the request guard (the start URL is). DNS rebinding between our check and the browser's own lookup is not fully prevented. The app is meant to run on a presenter's or analyst's machine, bound to 127.0.0.1, not as a public service.
- The deck check matches words, not meaning.
- Bot-protected sites may block the crawl.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Executable doesn't exist` when a run starts | Run `npx playwright install chromium`, or set `CHROMIUM_PATH` to an installed Chrome or Chromium |
| "Offline mode · no model key" | Expected without `ANTHROPIC_API_KEY`; replays still work. Restart the server after adding the key |
| SSL or proxy errors on a corporate network | Use replay mode, or run from a network that can reach the target site |
| "is not a full web address" | Type the full domain, for example `nike.com` |
| "Too many runs in progress" | Wait for a run to finish (3 at a time) |
| Port 3000 in use | `PORT=3001 npm start` |

## Releases

- **This branch:** Market Researcher, Tender Scout, review approvals with Knox, your own deck, marketplace list with MCP, guardrails (prompt injection, request guard, safe HTML, escalations), CI (ADR-043, ADR-044).
- **v0.5.x:** landing screen, report switcher, estimate tab, richer client deck, replay stop and speed, technology logos.
- **v0.4.x:** presentation for AI evaluation and its PowerPoint version, agent marketplace, deeper crawl with 132 technologies, review dashboard.
- **v0.3.0:** the animated presentation; product renamed to Nitro.
- **v0.2.x:** planner-driven lead, Lighthouse, replay, tech stack, pixel office, review window.
- **v0.1.0:** fixed pipeline; the always-working fallback (`git checkout v0.1.0`).

## Documentation

| Doc | Purpose |
| --- | --- |
| [01 · Requirements analysis](docs/01-requirements-analysis.md) | Problem, requirements, architecture, risks |
| [02 · Release plan](docs/02-release-plan.md) | Releases, exit gates, quality strategy |
| [03 · Demo plan](docs/03-demo-plan.md) | Run of show, fallback ladder, Q&A |
| [04 · Architecture](docs/04-architecture.md) | How it works in detail: formulas, extraction, estimate maths |
| [05 · Decision log](docs/05-decision-log.md) | Every design decision with context and consequences (44 entries) |
| [06 · Project summary](docs/06-project-summary.md) | Agents, skills, tools, what is verified and pending |
| [07 · Digithon write-up](docs/07-digithon-writeup.md) | The submission text |
| [08 · Cross-platform](docs/08-cross-platform.md) | Windows, macOS and Linux setup, restricted laptops, an installed Chrome |
| [Prompt history](docs/prompts.md) | The main prompts used to build Nitro with Claude Code |
| [SECURITY.md](SECURITY.md) | Threat model, controls, never-alone list |

## For reviewers: evidence by criterion

**Technical execution.** Runs end to end on real sites (saved traces in `runs/`, replayable). Error handling at every level: every tool retries once and posts failures ([`src/core/tool.ts`](src/core/tool.ts#L36)); failed inspectors are dropped and the score re-weighted ([`src/agents/audit.ts`](src/agents/audit.ts)); parallel steps settle independently ([`src/agents/lead.ts`](src/agents/lead.ts#L81)); a cut-off model page is salvaged or replaced by the template ([`src/agents/redesign.ts`](src/agents/redesign.ts)); offline fallbacks for every model call ([`src/core/llm.ts`](src/core/llm.ts#L10)). Ambiguous input gets clear messages ([`src/core/ssrf.ts`](src/core/ssrf.ts#L17)). 62 tests in [`src/test/`](src/test).

**Agent design.** A planning loop with 13 agents, 12 skills and 3 tools ([`executePlan`](src/agents/lead.ts#L52)); a model planner bounded by code guardrails with a rule fallback ([`validateDecision`](src/agents/planner.ts#L38), [`LlmPlanner`](src/agents/planner.ts#L87)); the reason and source of every decision are posted to the feed and saved in the trace; memory in the run context and replayable traces ([`saveTrace`](src/core/context.ts#L40)); escalation to a human with a stated reason ([`escalations`](src/agents/lead.ts#L108)); a never-alone list posted at the start of each run ([`NEVER_ALONE`](src/core/policy.ts#L3)).

**Business relevance.** Pre-sales for external business, with measured time and cost per analysis (see [Business case and pilot](#business-case-and-pilot)), a named-team estimate from the talent roster, a Knox approval step, and a pilot path with the metrics to track.

**Security and guardrails.** No secrets in the repo; keys come from the environment and CI scans for them. Untrusted content is data, never instructions ([`UNTRUSTED_RULE`](src/core/guard.ts#L6), [`injectionSignals`](src/core/guard.ts#L26)); private networks are blocked for every browser request ([`isAllowedRequest`](src/core/ssrf.ts#L45), [`newContext`](src/tools/browser.ts#L45)); model HTML is sanitised and served under a script-blocking CSP ([`sanitizeHtml`](src/core/guard.ts#L42), [`RUN_PAGE_CSP`](src/server.ts#L36)); read-only MCP with an origin check ([`handleMcp`](src/core/mcp.ts#L64)); human approval on every screen before Knox ([`web/review.html`](web/review.html#L82)). See [`SECURITY.md`](SECURITY.md).

**Product maturity and git sanity.** Working MVP across five screens, CLI, replay and MCP; CI on every push; tagged releases (`v0.1.0` to `v0.5.1`) with a fallback; a decision log of 44 entries; feature branches merged through pull requests; generated and uploaded files git-ignored.
