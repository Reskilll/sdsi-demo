# Proposal: Price homepage improvement

## Where you are today
Overall score **46/100 (F)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 23/100 (F). Lighthouse mobile score 23; main content in 19.7s, blocking time 2576 ms.
- **mobile**: 58/100 (D). 302 of 664 tap targets are too small on mobile.
- **a11y**: 0/100 (F). 13 accessibility rules failed (10 serious or critical).
- **ux**: 60/100 (D). Weakest area: visual hierarchy (2/5).
- **geo**: 97/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Main content takes 19.7s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 19668 ms (target < 2500 ms), FCP 12596 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 2.6s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 2576 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **302 tap targets are too small** — Mis-taps frustrate users right where you want them to act.
   - Evidence: 302 of 664 links/buttons are under 32px
   - Fix: Make interactive elements at least 44x44px with spacing between them.
4. **Certain ARIA roles must contain particular children** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-children: 8 element(s), e.g. .nv00-gnb-v4__l0-menu-list--left
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **Certain ARIA roles must be contained by particular parents** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-parent: 23 element(s), e.g. .nv00-gnb-v4__l0-menu-link[an-la="L0_2_shop"][href$="offer/"]
   - Fix: Fix the flagged elements and add automated a11y checks to CI.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 0→98, mobile 58→100, ux 60→72.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 32 days
- Responsive & mobile fixes: 11 days
- Accessibility remediation: 28 days
- UX & conversion redesign: 12 days
- QA & launch: 15 days
- Delivery management: 10 days

Total: 123 person-days over about 5 weeks.

## Team
Organisation skills match: **94/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Karan Shah, Performance Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)

## Commercials
Estimated range: **₹13,17,000 – ₹16,83,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8500 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
