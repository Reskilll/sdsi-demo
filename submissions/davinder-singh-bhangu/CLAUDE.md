# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm install              # Install dependencies
npm run dev              # Start Vite dev server (port 3000, hot-reload)
npm run build            # Production build → dist/
npm run preview          # Preview production build
```

## Architecture

**IT Service-Desk SLA Tracker** — single-page Vue 3 app (Vite + Composition API via options API style) that computes SLA breaches on support tickets.

### Core SLA Engine (`src/utils/slaEngine.js`)
The engine implements five rules:
- **M1**: SLA targets by priority (P1=4h, P2=8h, P3=24h, P4=72h), counted in business hours Mon–Fri 09:00–18:00 only.
- **M2**: Holidays (from `holidays.json`) are excluded; `isBusinessDay()` checks both day-of-week and the holiday set.
- **M3**: ON_HOLD status history entries pause the clock; `buildActiveIntervals()` splits the timeline into working segments, skipping hold periods.
- **M4**: Produces per-ticket `elapsedMin`, `dueBy`, `breach` (bool), and `breachMin`.
- **M5**: `computeSummary()` aggregates breach % by priority and by assignee group.

Key exported functions: `computeSLA(ticket, slaPolicy, holidays)`, `computeSummary(results)`, `addBusinessMinutes(start, minutes, bhStartMin, bhEndMin, holidaySet)`.

### Data flow
1. Sample JSON files load via `fetch` (or user uploads JSON via file input).
2. `App.vue` calls `computeSLA()` for each ticket → builds results array.
3. `computeSummary()` aggregates results → priority/group breach tables.
4. `TicketTable.vue` renders per-ticket rows; `SummaryPanel.vue` renders the two summary cards.

### Sample data files
- `tickets.json` — array of ticket objects with `id`, `priority`, `assigneeGroup`, `createdAt`, `resolvedAt`, `statusHistory[]`.
- `sla_policy.json` — business hours window and SLA targets per priority.
- `holidays.json` — array of `{ date, name }` objects.

### Component tree
```
App.vue
├── TicketTable.vue    (per-ticket SLA results table)
└── SummaryPanel.vue   (breach % by priority + by group)
```

### Notes
- The SLA engine is pure JavaScript with no Vue dependency — it can be tested/used standalone.
- Business hours and SLA targets are fully configurable via `sla_policy.json`.
- `slaEngine.js` is the only file with non-trivial logic; components are presentation-only.