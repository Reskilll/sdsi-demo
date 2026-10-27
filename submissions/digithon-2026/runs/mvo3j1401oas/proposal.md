# Proposal: Allbirds homepage improvement

## Where you are today
Overall score **64/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 38/100 (F). Lighthouse mobile score 38; main content in 17.6s, blocking time 776 ms.
- **mobile**: 87/100 (B). 12 of 84 tap targets are too small on mobile.
- **a11y**: 70/100 (C). 3 accessibility rules failed (2 serious or critical).
- **ux**: 60/100 (D). Weakest area: trust signals (2/5).
- **geo**: 65/100 (C). No structured data; llms.txt present.

## Priority fixes
1. **Main content takes 17.6s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 17559 ms (target < 2500 ms), FCP 6276 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 0.8s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 776 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **Buttons must have discernible text** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: button-name: 2 element(s), e.g. .text-current.swiper-prev-button.left-0
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
4. **Select element must have an accessible name** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: select-name: 1 element(s), e.g. .relative.w-full > select
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **No structured data for search and AI engines** — AI assistants and rich results rely on structured data to name and recommend the brand.
   - Evidence: No schema.org JSON-LD found on the homepage
   - Fix: Add Organization, WebSite and Product/Service JSON-LD.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 70→98, mobile 87→100, ux 60→60.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 21 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 18 days
- UX & conversion redesign: 12 days
- Structured data & AI-search: 7 days
- QA & launch: 13 days
- Delivery management: 9 days

Total: 103 person-days over about 4 weeks.

## Team
Organisation skills match: **88/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)

## Commercials
Estimated range: **₹10,71,000 – ₹13,68,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
