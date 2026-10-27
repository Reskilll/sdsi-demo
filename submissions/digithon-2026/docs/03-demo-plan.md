# 03 · Demo Plan: Nitro

**Demo moment:** a judge names any brand. We paste the URL. Its site is audited and redesigned live on screen.

**Format assumed:** 5–7 minute slot plus Q&A (adjust to the actual brief). Script timings are below.

## 1. The story arc

| Beat | Message | Emotion |
|---|---|---|
| Hook | "We have great developers and no clients." | Honest, relatable |
| Pain | Bench cost per month; proposals take days and don't win. | Urgency |
| Magic | A brand the judge chose gets audited and redesigned live. | Surprise |
| Proof | Before/after, a score uplift, real developers matched. | Conviction |
| Close | One won project pays for the bench. ROI panel. | Business sense |

## 2. Stage setup

| Item | Spec |
|---|---|
| Screens | Main: the command-centre UI, full screen, dark stage mode. Second device (or tab): backup replay, ready. |
| Presenter | One speaker drives, one "co-pilot" watches logs and the fallback. |
| Network | Venue Wi-Fi **and** a phone hotspot, both pre-tested. Wired if available. |
| Audio | Optional low ambient bed under the "agents working" section. |
| Browser | Fresh profile, 100% zoom, notifications off, tabs pre-opened: UI, replay, deck viewer. |

## 3. Run of show (≈ 6:30)

| Time | Presenter says / does | Screen |
|---|---|---|
| 0:00–0:30 | **Hook.** "We have great developers and no clients." Bench cost number: "₹/$X every month, idle." | Title slide with the live idle-cost counter ticking up |
| 0:30–1:00 | **Pain.** "Our proposals are slow, generic, and rarely win. Clients can't see what we'd do for *them*." | One slide: 3 stats |
| 1:00–1:20 | **Invite.** "Name a brand. Any brand." Judge answers. Presenter pastes the URL and clicks **Launch**. | UI: URL box → Launch |
| 1:20–2:00 | **Agents fan out.** Narrate the lead agent's plan as it appears. "The God agent just hired four specialists." Point at the feed: friendly lines streaming like a team chat, with every tool and skill call announcing itself ("Sending Lighthouse up the mountain…" then the result). Expand one message to show the detailed analysis behind it. | Four lanes in parallel + live agent chat feed with handoff arrows |
| 2:00–2:40 | **Audit lands first.** Walk through the report card: "They score D on mobile, nothing structured for AI search." Point at one evidence screenshot. | Report card, animated grade reveal |
| 2:40–4:00 | **Redesign appears.** Use the wait as storytelling: brand kit extracted, then the new homepage renders. | Brand kit → prototype building → final |
| 4:00–4:40 | **Before / after.** Drag the slider. Click through the nav and hover states in the prototype. "This is their site, improved, before they've signed anything." | Before/after slider, clickable prototype |
| 4:40–5:20 | **Team.** "Real developers who are free *now*." Reveal the **organisation match score** gauge ("we're an 82 for this client"), the skill-by-skill breakdown and one honest gap. Then the matched people, fit scores and the estimate. | Org match gauge → team panel + estimate |
| 5:20–5:50 | **Deck.** Open the generated deck: problem in their numbers, before/after, plan, price. "Ready for their CMO." | Deck viewer (slides 1, 3, 6) |
| 5:50–6:30 | **ROI close.** Toggle the ROI panel: "One won project covers the bench for N months." End on the pitch line. | ROI panel → closing line |

**Rule:** the audit appears within 60s and each lane keeps emitting visible progress, so there is never dead air.

## 4. The live-input protocol (the risky part)

The judge may name anything. Prepare three tiers:

| Tier | Brands | Approach |
|---|---|---|
| **Pre-warmed** | ~10 likely brands (e.g. well-known consumer, retail, auto, banking and electronics sites, **chosen after the R0 test run for reliability and visual quality**) | Results cached. Run executes "live" against warmed fetch/screenshots, so it is fast and safe. |
| **Live, uncached** | Anything else | Full live run, with every timeout and fallback active. |
| **Hostile** | Bot-blocked, login-walled, heavy SPA, non-English | Fall back to screenshot-only mode, or the presenter says "great pick, tough site, let me show you a similar run" and switches to a pre-warmed brand. |

**Judge steering (light-touch, honest):** ask "Name a brand you'd like to see; a consumer brand with a public website works best." Do not fake a live run. If a replay is used, label it "replay of an earlier run" aloud.

**Stage honesty rule:** if running from cache or replay, say so. Credibility with judges matters more than the effect.

## 5. Fallback ladder

| Failure | Detection | Response | Time cost |
|---|---|---|---|
| One agent is slow or errors | Lane stalls > 20s | The co-pilot hits **Retry lane**; the presenter continues with other lanes. | 0 |
| Site cannot be fetched | Fetch ladder exhausted | Screenshot-only mode, or a cached snapshot for known brands. | +15s |
| Model API outage / rate limit | Errors in the trace | Switch the toggle to **Replay mode** (streams a saved trace with real timings). | +5s |
| Venue network down | No egress | Hotspot; if that fails, local replay (no network needed). | +20s |
| Total failure | Anything | Play the recorded video; narrate over it. | +10s |

The co-pilot has a one-page runbook with each trigger and the key to press.

## 6. Demo data and assets to prepare

| Asset | Details | Owner |
|---|---|---|
| Pre-warmed runs | 10 brands, cached snapshots, traces, decks | Backend |
| Synthetic bench + hardcoded org skills | 30–40 developers and the 15–20 skill org inventory with realistic gaps, clearly labelled sample data. Check that the demo-list brands give a spread of match scores (e.g. 60s to 90s), not all 100. | Product |
| Feed copy review | Read the friendly lines for the 10 demo brands aloud, including every tool's start/end lines: funny, never insulting to the brand, never inventing facts. Check the start pools are big enough that no line repeats within a run. | Design |
| ROI defaults | Idle devs, loaded monthly cost, average project margin, baseline proposals/week and win rate. All editable, with sources noted. | Product |
| Backup video | Full 2-minute-compressed run of the best brand, with voice-over | Design |
| Exported decks | PPTX/PDF for the 3 safest brands | Backend |
| Runbook | Single page: triggers → actions | Presenter |
| Q&A sheet | See §8 | All |

## 7. Pre-flight checklist (T-60 → T-0)

- [ ] Build tag `v1.0-demo` deployed, health check green
- [ ] API keys valid, rate limits checked, budget headroom confirmed
- [ ] Fresh end-to-end run on a *new* brand passes (< 5 min)
- [ ] All 10 pre-warmed brands load from cache
- [ ] Replay mode streams correctly with the network disabled
- [ ] Backup video plays with sound on the venue machine
- [ ] Display resolution, projector scaling and dark mode verified
- [ ] Notifications, auto-updates and sleep disabled
- [ ] Hotspot connected as a secondary network
- [ ] Speaker and co-pilot sync on signals (e.g. "retry lane", "go replay")

## 8. Anticipated judge questions

| Question | Answer direction |
|---|---|
| "Is the redesign really generated live?" | Yes. Brand kit extraction and HTML generation run live. Be upfront about any caching. |
| "How accurate is the audit?" | Uses Lighthouse, axe-core and custom GEO checks; every finding links to evidence. The UX review is an LLM heuristic, labelled as such. |
| "Won't the client feel their site is being criticised?" | Framed as opportunities with business impact. The tone is tuned for a CMO, and a human reviews before sending. |
| "Are the developers real?" | The demo uses sample bench data. The schema plugs into the HRMS / resource tool for real data. |
| "What stops it from hallucinating numbers?" | Single source of truth: every number in the deck is pulled from the run context. A test enforces it. |
| "What does it cost per pitch?" | The UI shows the run cost (target under $2) versus days of bid-team effort. |
| "How do you measure success?" | Proposals per week, win rate, revenue, bench utilisation; baseline versus after, tracked per run. |
| "Legal / IP with using a brand's content?" | Public content, private concept, labelled as such, no public hosting. A human approves outreach. |
| "What's next?" | Real bench integration, CRM, RFP-first mode, a win/loss learning loop. |

## 9. Rehearsal plan

| Rehearsal | When | Focus | Pass criteria |
|---|---|---|---|
| Dry run 1 | R3 end (D9) | Script and timing with a friendly "judge" naming surprise brands | Finishes in 6:30 ± 30s |
| Chaos drill | D9 | Kill the network, slow the API, pick a blocked site; the co-pilot executes the runbook | Recovery within 30s each |
| Dress rehearsal | D10, venue hardware | Full run with Q&A | No unscripted failures |
| Final check | T-60 min | Pre-flight checklist | All boxes ticked |

## 10. Demo success criteria

- The judge-named brand produces audit, prototype, team and deck on screen.
- At least one **audible reaction** moment at the before/after reveal.
- The ROI line is delivered with the idle-cost counter in view.
- No dead air longer than 5 seconds.
- Every judge question has a ready answer from §8.

## 11. Closing line

> "We have great developers and no clients. Now every prospect gets to see their own better website, built by our team, before they sign. One win pays for the bench."
