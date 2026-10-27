# Proposal: Nike. Just Do It. Nike IN homepage improvement

## Where you are today
Overall score **60/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 37/100 (F). Lighthouse mobile score 37; main content in 16.9s, blocking time 1263 ms.
- **mobile**: 70/100 (C). 64 of 87 tap targets are too small on mobile.
- **a11y**: 45/100 (F). 6 accessibility rules failed (3 serious or critical).
- **ux**: 68/100 (C). Weakest area: trust signals (2/5).
- **geo**: 85/100 (B). Structured data found; no llms.txt.

## Priority fixes
1. **Main content takes 16.9s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 16894 ms (target < 2500 ms), FCP 3059 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 1.3s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 1263 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **64 tap targets are too small** — Mis-taps frustrate users right where you want them to act.
   - Evidence: 64 of 87 links/buttons are under 32px
   - Fix: Make interactive elements at least 44x44px with spacing between them.
4. **Elements must only use permitted ARIA attributes** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-prohibited-attr: 3 element(s), e.g. .css-1kexv9i
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **<ul> and <ol> must only directly contain <li>, <script> or <template> elements** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: list: 5 element(s), e.g. #\36 95780a4108b98bd4b9d2756 > .css-1qertln > .edgetoedgetextarea > .css-vwrx3n 
   - Fix: Fix the flagged elements and add automated a11y checks to CI.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 45→98, mobile 70→100, ux 68→60.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 25 days
- Responsive & mobile fixes: 7 days
- Accessibility remediation: 25 days
- UX & conversion redesign: 12 days
- Structured data & AI-search: 4 days
- QA & launch: 14 days
- Delivery management: 9 days

Total: 111 person-days over about 4 weeks.

## Team
Organisation skills match: **91/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)

## Commercials
Estimated range: **₹11,54,000 – ₹14,74,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
