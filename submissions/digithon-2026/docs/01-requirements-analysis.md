# 01 · Requirements Analysis: Nitro

> "We have great developers and no clients."

## 1. Problem and thesis

| | |
|---|---|
| **Problem** | Skilled developers sit on the bench. Proposals are slow, generic and rarely win. |
| **Thesis** | A prospect who sees *their own site, improved* before signing is far more likely to buy than one who reads a generic proposal. |
| **Product** | Paste a URL or RFP. A lead agent ("God agent") fans out to four specialist sub-agents and returns a complete, send-ready pitch package in minutes. |
| **Users** | Primary: sales / bid managers. Secondary: delivery managers (bench owners). Audience for the output: the prospect's CMO. |

## 2. Success metrics (from the brief)

| Metric | Baseline (assumed, to confirm) | Target |
|---|---|---|
| Proposals per week | 1–2 | 10+ |
| Time to first tailored pitch | 3–5 days | < 10 min |
| Win rate | ~10% | 20%+ |
| Bench utilisation | low | measurable lift |

**ROI model:** `monthly idle-bench cost = idle devs × loaded monthly cost`. Compare to the margin on **one** won project. The demo shows a live calculator: break-even is one win.
Baseline numbers are placeholders until Samsung provides real bench cost data. The UI must make them editable.

## 3. Capabilities (functional requirements)

Priority: **P0** = demo cannot work without it, **P1** = strongly improves the pitch, **P2** = stretch.

### F0. Intake and orchestration
| ID | Requirement | Pri |
|---|---|---|
| F0.1 | Accept a website URL (validate, normalise, follow redirects). | P0 |
| F0.2 | Accept an RFP (PDF / pasted text) and extract scope, requirements, budget and deadlines. | P1 |
| F0.3 | Lead agent plans the run and launches sub-agents **in parallel**, with dependencies where needed. | P0 |
| F0.4 | **Live agent feed** (see §5.2): a chat-style stream of what the agents are doing and saying to each other, with two layers per message: a short, human-friendly line and an expandable detailed analysis. Plus per-agent status, current step and partial results. | P0 |
| F0.4a | Feed shows handoffs explicitly ("Audit → Redesign: here are the 5 problems to fix") and who is waiting on whom. | P0 |
| F0.4b | A friendly-vs-technical toggle (default: friendly on stage). Every friendly line links to its evidence/detail. | P0 |
| F0.4d | **Every skill and tool execution posts to the feed**, automatically: a fun "starting" line when it begins (e.g. "Sending Lighthouse up the mountain…") and a "result" line when it ends (outcome, duration, and a headline number). No tool or skill can run without emitting events; this is enforced by the tool wrapper (§5.2), not left to each agent. | P0 |
| F0.4e | Tool posts are grouped under the agent that called them, collapsible, with a spinner while running, elapsed time, and failure/retry shown ("Lighthouse tripped, trying again"). High-frequency internals (e.g. individual page fetches) are rolled up into one post with a counter. | P0 |
| F0.4c | Agent personas (name, avatar, voice) and fun, short lines. Wording is generated from structured events, never a source of facts. | P1 |
| F0.5 | Graceful degradation: one agent failing must not kill the run. Show partial results and a retry. | P0 |
| F0.6 | Run history and shareable result page. | P2 |

### F1. Site audit (report card)
| ID | Requirement | Pri |
|---|---|---|
| F1.1 | **Speed:** Core Web Vitals (LCP, CLS, INP/TBT), page weight, Lighthouse performance. | P0 |
| F1.2 | **Mobile:** viewport, tap targets, responsive screenshots at 375 / 768 / 1440. | P0 |
| F1.3 | **UX:** LLM heuristic review of the screenshots (hierarchy, CTA clarity, navigation, trust signals). | P0 |
| F1.4 | **Accessibility:** axe-core violations, contrast, alt text, semantics. | P0 |
| F1.5 | **AI-search visibility (GEO):** structured data / schema.org, `llms.txt`, robots rules for AI crawlers, answerable content, entity clarity. | P0 |
| F1.6 | Letter grade per category, an overall score, and the top 5 prioritised fixes, each with business impact. | P0 |
| F1.7 | Evidence for every finding (metric, screenshot crop, selector). No unsupported claims. | P0 |

### F2. Redesigned prototype
| ID | Requirement | Pri |
|---|---|---|
| F2.1 | Extract the brand kit: logo, colours, fonts, tone, key copy and imagery from the live site. | P0 |
| F2.2 | Generate an improved homepage as real HTML/CSS that fixes the F1 findings and keeps the brand recognisable. | P0 |
| F2.3 | Clickable: nav, hover states, a responsive layout, 1–2 interactive sections. | P0 |
| F2.4 | Before / after slider or side-by-side view. | P0 |
| F2.5 | Annotated change list that maps each design change to an audit finding. | P1 |
| F2.6 | Rendered prototype re-audited with the same tools, showing a score uplift. | P1 |
| F2.7 | Export as a zip or a hosted preview link. | P2 |

### F3. Bench-matched team
| ID | Requirement | Pri |
|---|---|---|
| F3.1 | Bench roster data source (skills, seniority, availability dates, rate, past projects). Mock data for the demo, with a defined import schema (CSV/JSON). | P0 |
| F3.2 | Derive required skills from the audit and redesign (e.g. Next.js, a11y, performance, schema, CMS). | P0 |
| F3.3 | Match and rank available developers per role, with a rationale and a skill-fit score. | P0 |
| F3.4 | Estimate: effort by workstream, team, timeline and price range, with assumptions stated. | P0 |
| F3.5 | Show the idle cost recovered by this staffing (ties to ROI). | P1 |
| F3.6 | Soft-hold / reserve the matched developers. | P2 |
| F3.7 | **Organisation match score** (0–100): how well the *organisation's* skill inventory covers what this prospect needs, shown as a headline number with a per-skill breakdown (needed vs. have vs. available now) and the gaps. See §5.3. | P0 |
| F3.8 | Org skill inventory is **hardcoded** for now in one config file (`config/org-skills.json`), behind an interface so it can later be swapped for HRMS/resource data. | P0 |
| F3.9 | Score is deterministic and explainable: same inputs, same score. The LLM extracts the needed skills; code computes the score. | P0 |

### F4. Proposal and pitch deck
| ID | Requirement | Pri |
|---|---|---|
| F4.1 | Pitch deck of 8–10 slides, CMO-oriented: their problem in numbers, before/after, plan, team, price, next step. | P0 |
| F4.2 | Written proposal (scope, approach, timeline, team, commercials, terms placeholder). | P0 |
| F4.3 | Export to PPTX and PDF. | P0 |
| F4.4 | Consistent facts: every number comes from the audit, prototype or matcher outputs (single source of truth). | P0 |
| F4.5 | Cover email draft. Human review gate before anything is "sent". The system never sends on its own. | P1 |

## 4. Non-functional requirements

| Area | Requirement |
|---|---|
| **Latency** | Audit visible in ≤ 60s. Prototype in ≤ 3 min. Full package in ≤ 5 min. Progressive reveal so the screen is never idle. |
| **Reliability** | Demo-critical path ≥ 95% success on a list of 30 well-known brand sites. Per-step timeouts and fallbacks. |
| **Trust** | Findings cite evidence. The redesign is labelled "concept". Estimates show assumptions. |
| **Safety / legal** | Public pages only, respect robots.txt for crawling, no login-gated content. Never publish or send a prospect's brand assets outside the pitch. Prototypes are private, expiring links. Brand marks used for a pitch concept only. |
| **Security** | SSRF protection on the URL fetcher (block private IPs / metadata endpoints), sandboxed rendering of generated HTML (iframe `sandbox`, no external scripts), API keys server-side only. |
| **Cost** | Budget per run (target < $2 of model and compute). Track and display it. |
| **Observability** | Trace per run (agent steps, tokens, timings), for debugging and for the ROI story. |
| **Data privacy** | Bench data is internal. Mask rates in any prospect-facing output unless explicitly included. |

## 5. Agent architecture (proposed)

```
                      ┌──────────────────────────┐
 URL / RFP ──────────▶│  Lead agent (planner)    │──▶ progress stream (SSE)
                      │  plan · dispatch · merge │
                      └─────────────┬────────────┘
                shared run context (JSON): crawl, screenshots, scores
        ┌───────────────┬───────────┴───────┬────────────────┐
        ▼               ▼                   ▼                ▼
  ┌───────────┐  ┌──────────────┐   ┌──────────────┐  ┌──────────────┐
  │ Audit     │  │ Redesign     │   │ Bench match  │  │ Proposal &   │
  │ agent     │─▶│ agent        │   │ agent        │─▶│ deck agent   │
  │ (tools:   │  │ (brand kit → │   │ (roster      │  │ (assembles   │
  │ Playwright│  │ HTML proto)  │   │ query+rank)  │  │ everything)  │
  │ Lighthouse│  └──────┬───────┘   └──────┬───────┘  └──────────────┘
  │ axe, GEO) │         │ re-audit          │
  └───────────┘◀────────┘                   │
```

**Dependencies:** crawl → (audit ∥ brand-kit) → redesign → re-audit; bench match needs the audit's skill needs; the deck needs all of the above. Audit and bench-roster loading run in parallel with the crawl to hit the latency targets.

**Model usage (proposed):** lead agent on a top-tier model for planning and consistency, sub-agents on a faster model for volume work, and a vision-capable model for UX review and brand extraction. Final model choices are validated against cost and latency in the R0 spike.

**Tool layer:** Playwright (render, screenshots, DOM), Lighthouse or PageSpeed API (performance), axe-core (a11y), custom GEO checks, a roster store (SQLite/JSON), pptxgenjs (deck), and a headless Chrome PDF export.

### 5.1 F1 audit: agents or skills? (decision)

**Decision: one Audit agent that orchestrates five "inspectors". Only two inspectors are real LLM agents; three are plain tools wrapped as skills.** Making all five full agents adds latency, cost and flakiness for checks that are deterministic anyway.

| Inspector | Kind | How it works | Output |
|---|---|---|---|
| **Speed** | Tool-skill (no LLM judgment) | Lighthouse / PageSpeed API on mobile profile → LCP, CLS, TBT, page weight, top offenders. The LLM only phrases the finding. | Metrics, grade, evidence JSON |
| **Mobile** | Tool-skill | Playwright at 375 / 768 / 1440: viewport meta, horizontal overflow, tap-target size, font size, screenshots. | Checks, screenshots, grade |
| **Accessibility** | Tool-skill | axe-core run in Playwright → violations by impact, selectors, contrast failures. | Violations, grade |
| **UX** | **LLM agent (vision)** | Gets the screenshots and DOM outline, scores against a fixed rubric (hierarchy, CTA clarity, navigation, trust signals, copy clarity). Must cite a screenshot region for each finding. | Rubric scores, findings with crops |
| **AI-search (GEO)** | **LLM agent (text) + tool checks** | Tools check JSON-LD/schema.org, `llms.txt`, robots rules for AI crawlers, sitemap, heading structure. The LLM judges answerability and entity clarity: "could an AI assistant say what this company is and does from this page?" Optionally asks a model the prospect's category questions and records whether the brand is mentioned. | Checks, answerability notes, grade |

**Flow:** the Audit agent runs the crawl once, shares it with the inspectors, runs all five **in parallel**, then a synthesis step merges the results: grades per category, an overall score, and the top 5 fixes ranked by (impact × effort) with a business-impact sentence. Synthesis may only use numbers present in the inspector outputs.

**Why this split:** deterministic tools give trustworthy numbers that survive judge scrutiny. LLMs are used only where judgment is needed. The five-inspector view also makes a good stage visual, because each one appears as a named character in the feed (§5.2).

**Implementation:** each inspector is a typed function `inspect(runContext) → Finding[]` with a Zod schema. Tool-skills are plain code; the two LLM inspectors are small agent loops with a tool belt and a rubric prompt. They are packaged as skills (prompt + schema + tools) so they can be reused by other agents, for example the Redesign agent calls the Accessibility skill to re-audit its own prototype.

### 5.2 Live agent feed (F0.4)

Goal: it should feel like watching a team chat where specialists work, argue and hand work over, while staying honest about what is really happening.

**Event model.** Every agent step emits a structured event on the run's SSE stream. The UI renders the feed from events; no free-floating chatter.

```ts
type FeedEvent = {
  id: string; ts: number; runId: string;
  from: AgentId;                 // 'lead' | 'audit' | 'inspector.ux' | 'redesign' | 'bench' | 'deck' ...
  to?: AgentId | 'all';          // set for handoffs and questions
  kind: 'plan' | 'status' | 'finding' | 'handoff' | 'question' | 'answer'
      | 'tool_start' | 'tool_end' | 'skill_start' | 'skill_end'
      | 'partial_result' | 'warning' | 'done' | 'error';
  tool?: { name: string; callId: string; durationMs?: number; ok?: boolean; attempt?: number };
  friendly: string;              // one short, fun, human line (<= 140 chars)
  detail?: {                     // the serious layer, expandable
    summary: string;             // 2-4 sentences of analysis
    evidence?: EvidenceRef[];    // metric, screenshot crop, selector, trace link
    data?: unknown;              // structured payload for the panel
  };
  progress?: { step: number; of: number };
};
```

**How the two layers are produced.** Agents emit the structured `detail` themselves. The `friendly` line comes from a persona-voiced rewrite of the event by a small, fast model, with a deterministic template as the fallback so the feed never blocks on it. The friendly line may not add facts that are not in `detail`.

**Example (what the audience sees):**

| | Friendly line | Detail (on expand) |
|---|---|---|
| 🧭 Lead → all | "New case! Let's see what's up with acme.com. Everyone to your stations." | Plan: crawl → audit ∥ brand-kit ∥ roster load → redesign → match → deck |
| 🔬 Speed | "Whoa, 6.2 s to show the hero image. That's a coffee break." | LCP 6.2 s (mobile), hero 2.4 MB PNG, 14 render-blocking scripts |
| 👁 UX → Lead | "Found 3 'Buy' buttons all shouting at once. Nobody knows where to click." | Rubric: CTA clarity 2/5. Screenshot crop attached |
| 🔎 Audit → Redesign | "Handing you the top 5 problems. #1 is mobile nav." | Handoff payload: ranked fixes with evidence |
| 🎨 Redesign → Audit | "Rebuilt it. Can you check my homework?" | Re-audit request for the prototype |
| 🧑‍💻 Bench → Lead | "Good news: 4 of the 5 skills we need are free next week." | Org match 82; gap: Shopify Plus (0 available) |

**Tool and skill posts (F0.4d).** All tools and skills are registered through one `defineTool` / `defineSkill` wrapper that emits `*_start` and `*_end` events around every call, so coverage is automatic and tamper-proof. Each registration carries a small **feed spec** next to its schema:

```ts
defineTool({
  name: 'lighthouse.run',
  feed: {
    start: ["Sending Lighthouse up the mountain…", "Stopwatch out, let's time this page."],
    end:   (r) => `Page took ${r.lcp}s to show its hero. ${r.lcp > 4 ? 'Ouch.' : 'Not bad!'}`,
    error: "Lighthouse tripped on a cable. Trying again.",
    headline: (r) => `LCP ${r.lcp}s`,
  },
  run: async (input, ctx) => { /* ... */ },
});
```

- `start` is a pool of lines (rotated so repeats don't get stale); `end` and `error` are templates over the real result, so the numbers are always true. The optional persona rewrite (F0.4c) applies on top.
- The wrapper adds the agent, `callId`, duration and attempt count, links the post to the evidence the tool produced, and attaches the tool's output to `detail`.
- A skill post wraps its inner tool posts (skill start → tools → skill end), so the feed reads as a nested story: "Accessibility inspector: warming up axe…" → "axe found 23 issues, 4 serious".
- Noisy tools are rolled up (one post with a live counter, e.g. "Crawled 7/12 pages").
- Lint rule and unit test: any tool or skill without a `feed` spec fails CI.

**UI.** Chat-style stream with avatars and typing indicators, handoff arrows between agent lanes, a pinned "what's happening now" strip, and a toggle for friendly/technical. Clicking a message opens its detail and evidence in a side panel. Partial results (grades, screenshots) pop into their panels as events arrive. The feed is recorded in the trace, which also powers replay mode.

### 5.3 Organisation match score (F3.7, F3.8)

**Meaning:** "How ready is our organisation, by skills, to deliver what this prospect needs?" This is a headline number for the CMO deck and the stage. It is separate from the per-developer fit scores.

**Inputs.**
1. *Needed skills* with weights, derived from the audit findings, the redesign and (later) the RFP: for example `{a11y: 0.9, web-performance: 1.0, nextjs: 0.8, schema-seo: 0.6, design-systems: 0.7}`. The LLM proposes skills from a **controlled vocabulary** (the keys in the org skill file); weights come from finding severity, computed by code.
2. *Hardcoded org skill inventory* in `config/org-skills.json`:

```json
{
  "skills": [
    { "id": "nextjs", "label": "Next.js / React", "level": 4, "headcount": 12, "available": 5, "availableFrom": "2026-11-02" },
    { "id": "web-performance", "label": "Web performance", "level": 4, "headcount": 4, "available": 2, "availableFrom": "2026-11-02" },
    { "id": "a11y", "label": "Accessibility (WCAG)", "level": 3, "headcount": 3, "available": 1, "availableFrom": "2026-11-09" },
    { "id": "schema-seo", "label": "Structured data / SEO / GEO", "level": 3, "headcount": 2, "available": 1, "availableFrom": "2026-11-02" },
    { "id": "ux-design", "label": "UX / UI design", "level": 4, "headcount": 6, "available": 2, "availableFrom": "2026-11-02" },
    { "id": "shopify", "label": "Shopify / commerce", "level": 2, "headcount": 2, "available": 0, "availableFrom": null }
  ]
}
```

   Levels are 1–5. About 15–20 skills are enough, with realistic gaps so the score is not always 100.

**Formula (deterministic, explainable).** For each needed skill *s* with weight *wₛ*:
- `depth(s)` = `min(1, available / required_headcount)`, where required headcount comes from the effort estimate. It is 0 if no one is available.
- `proficiency(s)` = `level / 5`, capped at the needed level.
- `fit(s)` = `0.6 × proficiency + 0.4 × depth`.
- **Org match score** = `100 × Σ(wₛ × fit(s)) / Σ(wₛ)`.

Output also lists the top strengths, the gaps (skills with fit < 0.5) and "ready by" dates from `availableFrom`. A gap is shown honestly with a mitigation hint ("hire/partner for Shopify Plus"). Weights and the 0.6/0.4 split are config, so they can be tuned and defended.

**Where it shows up.** The Bench agent's result panel (a gauge + a skill-by-skill bar view), a deck slide ("Why us"), the ROI panel (higher match → higher win probability assumption, clearly labelled as an assumption), and the feed.

**Later:** replace the JSON loader with an HRMS / resource-planning adapter implementing the same `OrgSkillProvider` interface.

## 6. Key risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Live demo fails** (site blocks bots, slow, CAPTCHA, SPA doesn't render). | High | Critical | Pre-warmed cache for ~10 likely brands, a robust fetch ladder (Playwright → plain HTTP → cached snapshot), a judge-named brand is run live with a fallback "rehearsed" run on standby. See demo plan. |
| 2 | Redesign looks generic or breaks the brand. | Med | High | Brand-kit-first prompting, a design-token layer, a curated component library to compose from, and a vision self-critique loop (max 2 passes). |
| 3 | Run takes too long for the stage. | High | High | Parallelism, progressive reveal, a stage script that fills the wait with narration, and streaming partial results. |
| 4 | Audit claims are wrong or embarrassing for a famous brand. | Med | High | Evidence-only findings, tone guidelines ("opportunities"), verification of any numeric claim against tool output. |
| 5 | Bench data isn't real or available. | High | Med | Realistic synthetic roster plus a CSV import. Be explicit in the demo that the data is sample data. |
| 6 | Scope creep across four agents in a short timeline. | High | High | Strict P0 cut line, vertical slice first (R1), and feature freeze before the dress rehearsal. |
| 7 | Legal / brand concerns over redesigning a real company's site. | Low | Med | "Concept for pitch purposes" labelling, no public hosting, and a disclaimer in the footer. |
| 8 | Model or API outage or rate limits during the demo. | Low | Critical | A recorded full-run fallback video, cached outputs, and a local mode that replays a saved trace. |

## 7. Assumptions and open questions

1. **Timeline:** the Digithon 2026 deadline and the demo date are not given. The release plan assumes ~10 working days and is expressed in relative days.
2. **Team size:** the plan assumes 3–4 people (frontend, agents/backend, design/demo). Please confirm.
3. **Stack:** TypeScript end to end (Next.js UI and Node agent runtime) is assumed. Confirm any Samsung or hackathon constraints on tools or cloud.
4. **Model access:** the plan assumes the Claude API is available. Confirm keys and rate limits.
5. **Bench data:** is any real (anonymised) roster available? Otherwise synthetic.
6. **Judging criteria:** emphasis on innovation vs. feasibility vs. business impact? This changes the demo's weighting.
7. **RFP intake (F0.2):** is it required for the demo, or is the URL path enough? Assumed P1.

## 8. Scope decision

- **In (MVP, P0):** URL intake, the full four-agent chain, live progress, audit report card, redesigned homepage with before/after, the bench match with an estimate, a PPTX/PDF deck, and an ROI panel.
- **Fast-follow (P1):** RFP intake, re-audit uplift, annotated change list, proposal document, cover email.
- **Out for now (P2):** multi-page redesign, CRM integration, auto-send, soft-hold of developers, run history.
