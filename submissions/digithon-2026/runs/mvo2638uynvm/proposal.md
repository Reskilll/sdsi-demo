# Proposal: Stripe homepage improvement

## Where you are today
Overall score **69/100 (C)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 43/100 (F). Lighthouse mobile score 43; main content in 4.7s, blocking time 1310 ms.
- **mobile**: 70/100 (C). 103 of 180 tap targets are too small on mobile.
- **ux**: 76/100 (C). Weakest area: cta clarity (3/5).
- **geo**: 90/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Main content takes 4.7s to appear on mobile** — Every extra second of load time costs conversions; slow pages also rank lower in search.
   - Evidence: Lighthouse mobile LCP 4714 ms (target < 2500 ms), FCP 3814 ms
   - Fix: Compress and preload the hero image, defer non-critical scripts, serve via a CDN.
2. **Page is unresponsive for 1.3s while loading** — Taps and scrolls feel broken while scripts run, so visitors leave before they act.
   - Evidence: Total blocking time 1310 ms (target < 200 ms)
   - Fix: Split and defer JavaScript, remove unused third-party scripts.
3. **103 tap targets are too small** — Mis-taps frustrate users right where you want them to act.
   - Evidence: 103 of 180 links/buttons are under 32px
   - Fix: Make interactive elements at least 44x44px with spacing between them.
4. **Headline text collides with the colorful gradient artwork** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: The right end of the H1 and the first lines of the subhead ('your revenue.', 'services and', '– from') sit over the purple/pink ribbon. The slate-blue text loses contrast there and the purple highlighted words nearly blend into the artwork.
   - Fix: Shift the ribbon artwork right or lower, or keep the text column clear of it. Alternatively, add a white-to-transparent gradient behind the text, or keep the headline text colors consistent and high-contrast.
5. **Primary CTA competes with header CTAs and is vague** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: 'Request an invite' is the only hero button, in the same indigo as the header 'Contact sales'. The label doesn't say what the invite is for, and there is no secondary path such as 'Start now' or 'See pricing' for self-serve visitors. The header's 'Sign in' is a white button with orange text, which is a weak, inconsistent style.
   - Fix: Make the hero CTA specific, e.g. 'Request an invite to [product]' or 'Get started'. Add a secondary text or ghost button, and give 'Sign in' a standard low-emphasis link style.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: mobile 70→100, ux 76→76.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Performance engineering: 14 days
- Responsive & mobile fixes: 7 days
- UX & conversion redesign: 12 days
- QA & launch: 8 days
- Delivery management: 5 days

Total: 61 person-days over about 3 weeks.

## Team
Organisation skills match: **96/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Ananya Rao, UX Designer (free from 2026-11-02)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Diya Nair, Frontend Engineer (free from 2026-11-02)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)

## Commercials
Estimated range: **₹6,21,000 – ₹7,94,000**.
Assumptions:
- Homepage and key templates only; no new backend features
- Client provides brand assets and timely feedback
- Blended day rate 8083 with a 40% margin
- Estimate is +/- range until discovery is complete

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
