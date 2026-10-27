# Proposal: HDFC Bank homepage improvement

## Where you are today
Overall score **79/100 (C)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 68/100 (C). Lighthouse mobile score 68; main content in 4.1s, blocking time 233 ms.
- **mobile**: 81/100 (B). 92 of 289 tap targets are too small on mobile.
- **a11y**: 87/100 (B). 3 accessibility rules failed (1 serious or critical).
- **ux**: 68/100 (C). Weakest area: navigation (2/5).
- **geo**: 100/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Main content takes 4.1s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 4081 ms (target < 2500 ms), FCP 1681 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Layout jumps while loading** — Shifting layouts cause mis-clicks and make the brand feel unreliable.
   - Evidence: Lighthouse CLS 0.257 (target < 0.1)
   - Fix: Reserve space for images, ads and embeds; avoid late-injected banners.
3. **92 tap targets are too small** — Mis-taps frustrate users right where you want them to act.
   - Evidence: 92 of 289 links/buttons are under 32px
   - Fix: Make interactive elements at least 44x44px with spacing between them.
4. **<html> element must have a lang attribute** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: html-has-lang: 1 element(s), e.g. html
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **Navigation has 8 items** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: NRI · HNI · Wholesale · Agri · MSME · Government Schemes · Discover Products · Need Help
   - Fix: Group into 5-7 top-level items with clear labels.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 87→98, mobile 81→100, ux 68→68.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 14 days
- Responsive & mobile fixes: 7 days
- Accessibility remediation: 15 days
- UX & conversion redesign: 4 days
- QA & launch: 9 days
- Delivery management: 6 days

Total: 70 person-days over about 3 weeks.

## Team
Organisation skills match: **95/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Ananya Rao, UX Designer (free from 2026-11-02)

## Commercials
Estimated range: **₹7,28,000 – ₹9,30,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
