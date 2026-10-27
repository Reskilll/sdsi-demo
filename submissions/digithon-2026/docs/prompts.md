# Prompt history

A short record of how Nitro was built with Claude Code: the main prompts, in order, lightly edited for length. Each one led to one or more commits; the reasons behind the bigger choices are in the [decision log](05-decision-log.md).

## 1. The product

- Build an AI pre-sales tool: paste a prospect's website, and a team of agents audits it, redesigns the homepage, matches our available people, and writes a pitch deck. Plan it first (requirements, release plan, demo plan).
- Make the lead agent plan its own steps, with guardrails, instead of a fixed sequence. Keep v0.1.0 as a fallback.
- Add Lighthouse for speed, a tech-stack detector that reads network traffic, and replay so a saved run can be shown for free.
- Give the agents pixel robots, an office, result cards and a review window. Rename the product to Nitro.

## 2. The story and the presentation

- Write a presentation for the Digithon: the problem, the idea, how it works, real results. Keep the language simple, B2B and professional.
- Don't use the word "bench". Don't invent numbers: only use figures we measured.
- Make a PowerPoint version that stays in sync with the HTML deck, with speaker notes.
- Restructure into a short main track with an appendix, click-driven builds, canvas-like transitions and a slide tray.
- Rework the pain-point slides: why conversion is low, the generic proposal that lands in the client's unread inbox, demos that take days, a "What if" moment with a big bang.
- Redo the RFP slide as a volume play: a few RFPs a month versus hundreds of prospects, with the maths, and reaching the CTO first.
- Show that the website is only the way in: talk about backend, cloud, data pipelines and logistics with keywords, icons and animation, not text.
- New title line, "Powering external business in a supercharged environment", with a rocket-curtain transition.

## 3. More agents and screens

- Add a landing screen with a pipeline of companies being processed, and replay for the Nike run.
- Add a Market Researcher that finds the latest news about the company first (simulated for now, shown as callouts in the Nike replay).
- Add a Tender Scout that triages government tenders and RSS feeds, shown on the home dashboard with a government icon and a glow.
- On the review screen: Approve and Request changes on every screen, and a "Submit Knox Approval" button that unlocks only when all are approved. Let people upload their own deck and check it against our analysis.
- Turn the agent marketplace into a list with active or idle status, and a way to connect any agent over MCP.

## 4. Quality and release

- Track tokens and cost per agent and per run.
- Review the code against the Digithon criteria (technical execution, agent design, business relevance, security and guardrails, product maturity) and fix the gaps; make the README complete and add evidence for each criterion.
- Make it work on Windows, macOS and Linux, add tests, check the Nike run, and merge to main.
- Next: a login screen.
