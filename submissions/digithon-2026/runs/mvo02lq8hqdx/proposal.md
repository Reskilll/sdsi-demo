# Proposal: Samsung India homepage improvement

## Where you are today
Overall score **60/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 28/100 (F). Lighthouse mobile score 28; main content in 6.7s, blocking time 1105 ms.
- **mobile**: 81/100 (B). 19 of 268 tap targets are too small on mobile.
- **a11y**: 35/100 (F). 5 accessibility rules failed (5 serious or critical).
- **ux**: 68/100 (C). Weakest area: navigation (2/5).
- **geo**: 97/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Main content takes 6.7s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 6690 ms (target < 2500 ms), FCP 4158 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 1.1s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 1105 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **Certain ARIA roles must contain particular children** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-children: 2 element(s), e.g. .nv00-gnb-v4__l0-menu-list--left
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
4. **Certain ARIA roles must be contained by particular parents** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-parent: 17 element(s), e.g. .nv00-gnb-v4__l0-menu-link[an-la="L0_2_shop"][href$="offer/"]
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **Navigation has 8 items** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: Shop Explore Shop · Mobile · TV & AV · Appliances · Computers & Monitors · Wearables · Accessories · Samsung Week
   - Fix: Group into 5-7 top-level items with clear labels.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 35→98, mobile 81→100, geo 97→97, ux 68→68.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 26 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 28 days
- UX & conversion redesign: 4 days
- QA & launch: 13 days
- Delivery management: 9 days

Total: 103 person-days over about 4 weeks.

## Team
Organisation skills match: **95/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Karan Shah, Performance Engineer (free from 2026-11-02)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)

## Commercials
Estimated range: **₹10,82,000 – ₹13,82,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8333 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
