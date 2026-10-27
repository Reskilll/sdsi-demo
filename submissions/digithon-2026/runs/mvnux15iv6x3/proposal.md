# Proposal: Example Domain homepage improvement

## Where you are today
Overall score **77/100 (C)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 100/100 (A). Main content shows in 0.2s; 0.0 MB over 2 requests.
- **mobile**: 100/100 (A). 1 of 1 tap targets are too small on mobile.
- **a11y**: 90/100 (A). 3 accessibility rules failed (0 serious or critical).
- **ux**: 64/100 (D). Weakest area: visual hierarchy (2/5).
- **geo**: 21/100 (F). No structured data; no llms.txt.

## Priority fixes
1. **No structured data for search and AI engines** — AI assistants and rich results rely on structured data to name and recommend the brand.
   - Evidence: No schema.org JSON-LD found on the homepage
   - Fix: Add Organization, WebSite and Product/Service JSON-LD.
2. **No main headline (h1)** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: 0 h1 elements
   - Fix: Use exactly one clear headline stating the value proposition.
3. **Document should have one main landmark** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: landmark-one-main: 1 element(s), e.g. html
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
4. **Page should contain a level-one heading** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: page-has-heading-one: 1 element(s), e.g. html
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **No llms.txt guide for AI crawlers** — A cheap, early signal that helps AI tools represent the brand accurately.
   - Evidence: https://example.com/llms.txt not found
   - Fix: Publish an llms.txt summarising the site and its key pages.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 90→98, mobile 100→100, geo 21→36, ux 64→64.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Accessibility remediation: 12 days
- UX & conversion redesign: 4 days
- Structured data & AI-search: 15 days
- QA & launch: 7 days
- Delivery management: 5 days

Total: 58 person-days over about 2 weeks.

## Team
Organisation skills match: **87/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)
- Kabir Singh, SEO / Schema Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)

## Commercials
Estimated range: **₹5,85,000 – ₹7,47,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8000 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
