# Proposal: Samsung India homepage improvement

## Where you are today
Overall score **60/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 36/100 (F). Lighthouse mobile score 36; main content in 17.4s, blocking time 799 ms.
- **mobile**: 81/100 (B). 19 of 269 tap targets are too small on mobile.
- **a11y**: 35/100 (F). 5 accessibility rules failed (5 serious or critical).
- **ux**: 60/100 (D). Weakest area: cta clarity (2/5).
- **geo**: 97/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Main content takes 17.4s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 17445 ms (target < 2500 ms), FCP 7895 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 0.8s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 799 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **Certain ARIA roles must contain particular children** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-children: 2 element(s), e.g. .nv00-gnb-v4__l0-menu-list--left
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
4. **Certain ARIA roles must be contained by particular parents** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-parent: 16 element(s), e.g. .nv00-gnb-v4__l0-menu-link[an-la="L0_2_shop"][href$="offer/"]
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
5. **No visible primary CTA in the hero** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: The hero shows 'The all-new Galaxy Z Fold8 Ultra | Fold8 | Flip8' with no button such as 'Pre-order', 'Learn more' or 'Buy now'. The only visible actions are the small header icons (search, cart, account) and the 'Shop' nav link. The CTA list above the fold also includes 'Shop Explore Shop', which looks like a duplicated or mislabeled item.
   - Fix: Add a prominent button pair under the headline, such as 'Pre-order now' (primary) and 'Learn more' (secondary). Use a high-contrast fill and put it within the first viewport. Clean up the duplicated 'Shop Explore Shop' label.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 35→98, mobile 81→72, ux 60→68.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 28 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 28 days
- UX & conversion redesign: 12 days
- QA & launch: 14 days
- Delivery management: 10 days

Total: 115 person-days over about 4 weeks.

## Team
Organisation skills match: **93/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)

## Commercials
Estimated range: **₹11,95,000 – ₹15,27,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
