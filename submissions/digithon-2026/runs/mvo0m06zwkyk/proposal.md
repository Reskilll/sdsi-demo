# Proposal: Samsung India homepage improvement

## Where you are today
Overall score **73/100 (C)** on speed, mobile, accessibility, UX and AI-search visibility.

- **speed**: 92/100 (A). Main content shows in 0.6s; 2.1 MB over 103 requests.
- **mobile**: 81/100 (B). 19 of 268 tap targets are too small on mobile.
- **a11y**: 35/100 (F). 5 accessibility rules failed (5 serious or critical).
- **ux**: 68/100 (C). Weakest area: navigation (2/5).
- **geo**: 97/100 (A). Structured data found; llms.txt present.

## Priority fixes
1. **Certain ARIA roles must contain particular children** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-children: 2 element(s), e.g. .nv00-gnb-v4__l0-menu-list--left
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
2. **Certain ARIA roles must be contained by particular parents** — Inaccessible sites exclude users, invite legal risk (ADA / EAA) and lose search visibility.
   - Evidence: aria-required-parent: 17 element(s), e.g. .nv00-gnb-v4__l0-menu-link[an-la="L0_2_shop"][href$="offer/"]
   - Fix: Fix the flagged elements and add automated a11y checks to CI.
3. **Navigation has 8 items** — Visitors decide in seconds; unclear hierarchy and actions send them to a competitor.
   - Evidence: Shop Explore Shop · Mobile · TV & AV · Appliances · Computers & Monitors · Wearables · Accessories · Samsung Week
   - Fix: Group into 5-7 top-level items with clear labels.
4. **19 tap targets are too small** — Mis-taps frustrate users right where you want them to act.
   - Evidence: 19 of 268 links/buttons are under 32px
   - Fix: Make interactive elements at least 44x44px with spacing between them.
5. **Text is too small to read comfortably** — Unreadable copy means the message never lands.
   - Evidence: 21 text blocks under 12px
   - Fix: Use a 16px base font size and a fluid type scale.

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: a11y 35→98, mobile 81→100, geo 97→97, ux 68→68.

## Approach and timeline
- Homepage rebuild (design + front end): 15 days
- Responsive & mobile fixes: 8 days
- Accessibility remediation: 28 days
- UX & conversion redesign: 4 days
- QA & launch: 9 days
- Delivery management: 6 days

Total: 70 person-days over about 3 weeks.

## Team
Organisation skills match: **93/100**.
- Aarav Mehta, Senior Frontend Engineer (free from 2026-11-02)
- Dev Malhotra, Senior Frontend Engineer (free from 2026-11-09)
- Isha Patel, QA Automation Engineer (free from 2026-11-09)
- Vikram Das, Design Systems Engineer (free from 2026-11-02)
- Zoya Ali, Accessibility Specialist (free from 2026-11-02)
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
