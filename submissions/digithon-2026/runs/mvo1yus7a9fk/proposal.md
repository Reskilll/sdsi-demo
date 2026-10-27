# Proposal: Allbirds homepage improvement

## Where you are today
Overall score **63/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 38/100 (F). Lighthouse mobile score 38; main content in 21.3s, blocking time 738 ms.
- **mobile**: 87/100 (B). 12 of 84 tap targets are too small on mobile.
- **a11y**: 70/100 (C). 3 accessibility rules failed (2 serious or critical).
- **ux**: 56/100 (D). Weakest area: visual hierarchy (2/5).
- **geo**: 65/100 (C). No structured data; llms.txt present.

## Priority fixes
1. **Blocking shipping modal hides the hero and the page's primary message** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: A white 'Where are we shipping to?' modal sits over the center of the hero, and a dark overlay dims the rest of the page. The H1 'Wildly Comfortable. Super Natural.' is dimmed and sits low on the right. Before any browsing, the visitor has to dismiss the modal by choosing a country and clicking CONFIRM or the X.
   - Fix: Replace the modal with a non-blocking banner or a geo-detected default (e.g. 'Shipping to United States – change'). If a modal is kept, show it only when the detected country differs from the site's, and make it easy to dismiss.
2. **Hero headline and CTAs have low contrast and low prominence** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: The headline is pale gray text on a gray gravel background at the lower right, and the 'ALL NEW DASHER NZ COLLECTION' eyebrow is monospace and barely readable. The SHOP MEN and SHOP WOMEN pills are small, gray on gray, and visually weak compared with the black CONFIRM button. The page lists many CTAs (Shop Socks, Sale, and others), but none stands out as the primary action.
   - Fix: Add a scrim or move the text to a plain area. Use a larger white or dark headline with a solid high-contrast primary button (e.g. black 'Shop Men' and 'Shop Women'). Limit hero CTAs to one or two.
3. **Main content takes 21.3s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 21254 ms (target < 2500 ms), FCP 6785 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
4. **Page is unresponsive for 0.7s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 738 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
5. **Buttons must have discernible text** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: button-name: 2 element(s), e.g. .text-current.swiper-prev-button.left-0
   - Fix: Fix the flagged elements and add automated a11y checks to CI.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 70→83, mobile 87→100, geo 65→62, ux 56→60.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 25 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 18 days
- UX & conversion redesign: 21 days
- Structured data & AI-search: 7 days
- QA & launch: 15 days
- Delivery management: 10 days

Total: 119 person-days over about 4 weeks.

## Team
Organisation skills match: **92/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)

## Commercials
Estimated range: **₹12,37,000 – ₹15,81,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
