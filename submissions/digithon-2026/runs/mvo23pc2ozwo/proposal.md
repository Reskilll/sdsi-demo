# Proposal: Allbirds homepage improvement

## Where you are today
Overall score **63/100 (D)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 41/100 (F). Lighthouse mobile score 41; main content in 24.0s, blocking time 583 ms.
- **mobile**: 87/100 (B). 12 of 84 tap targets are too small on mobile.
- **a11y**: 70/100 (C). 3 accessibility rules failed (2 serious or critical).
- **ux**: 56/100 (D). Weakest area: visual hierarchy (2/5).
- **geo**: 65/100 (C). No structured data; llms.txt present.

## Priority fixes
1. **Blocking shipping modal hides the hero and primary content on first load** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: A white 'Where are we shipping to?' modal sits in the center of the viewport over a dimmed hero. The H1 'Wildly Comfortable. Super Natural.' and the product imagery are darkened and partly covered. The modal's near-black CONFIRM button is the strongest element on screen, so it pulls attention from the brand message and the shop CTAs.
   - Fix: Replace the modal with a dismissible top banner or a country suggestion inside the header. If a modal has to stay, preselect the country from geo-IP and show it only to visitors whose location differs from the store. Never block the hero for US visitors.
2. **Hero headline and CTAs have weak contrast and are visually secondary** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: The 'Wildly Comfortable. Super Natural.' headline is light gray on a mottled gray pavement photo at the lower right, and it is small relative to the hero. The eyebrow text 'ALL NEW DASHER NZ COLLECTION' is thin monospace and almost illegible. The SHOP MEN and SHOP WOMEN pills are gray on gray with little affordance. The vertical 'DASHER NZ' text strip adds clutter.
   - Fix: Add a dark gradient overlay or move the copy to a calmer area of the image. Make the headline larger and white with a heavier weight. Style the primary CTA as a solid, high-contrast button, such as white fill with dark text, and make the secondary CTA an outline. Increase the eyebrow size and weight.
3. **Main content takes 24.0s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 23972 ms (target < 2500 ms), FCP 5948 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
4. **Reduce unused JavaScript: about 2.8s to gain** — Faster pages convert better and rank higher.
   - Evidence: Lighthouse opportunity, estimated saving 2760 ms
   - Fix: Address "Reduce unused JavaScript".
5. **Buttons must have discernible text** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: button-name: 2 element(s), e.g. .text-current.swiper-prev-button.left-0
   - Fix: Fix the flagged elements and add automated a11y checks to CI.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 70→96, mobile 87→100, geo 65→62, ux 56→60.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 18 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 18 days
- UX & conversion redesign: 21 days
- Structured data & AI-search: 7 days
- QA & launch: 14 days
- Delivery management: 9 days

Total: 110 person-days over about 4 weeks.

## Team
Organisation skills match: **92/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)

## Commercials
Estimated range: **₹11,43,000 – ₹14,61,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8250 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
