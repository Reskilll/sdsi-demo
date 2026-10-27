# IT Service-Desk SLA Tracker

A Vue 3 single-page application that computes SLA breaches for support tickets, respecting business hours, holidays, and ticket hold periods.

## SLA Rules

| Rule | Description |
|------|-------------|
| **M1** | SLA targets by priority — P1: 4h, P2: 8h, P3: 24h, P4: 72h (business hours only, Mon–Fri 09:00–18:00) |
| **M2** | Holidays are excluded from SLA time |
| **M3** | SLA clock pauses while a ticket is `ON_HOLD` |
| **M4** | Per-ticket report: elapsed business minutes, due-by time, breach yes/no, breach minutes |
| **M5** | Summary: breach % per priority and per assignee group |

## Quick Start

```bash
npm install
npm run dev
```

Opens at `http://localhost:3000`.

## Data Files

| File | Purpose |
|------|---------|
| `tickets.json` | Array of ticket objects with status history |
| `sla_policy.json` | Business hours window and SLA targets per priority |
| `holidays.json` | Array of holiday dates to exclude |

The UI supports uploading custom JSON files in place of the defaults.

## Project Structure

```
davinder-singh-bhangu/
├── public/
├── src/
│   ├── main.js                  # Vue app entry
│   ├── App.vue                  # Root: controls, uploads, orchestrates SLA computation
│   ├── components/
│   │   ├── TicketTable.vue      # Per-ticket SLA results table
│   │   └── SummaryPanel.vue     # Breach % by priority & assignee group
│   └── utils/
│       └── slaEngine.js         # Pure-JS SLA calculator (business-minutes, holidays, ON_HOLD)
├── tickets.json
├── sla_policy.json
├── holidays.json
├── index.html
├── vite.config.js
└── package.json
```

## SLA Engine API

The engine (`src/utils/slaEngine.js`) is framework-agnostic and can be used standalone:

```js
import { computeSLA, computeSummary } from './src/utils/slaEngine.js';

const result = computeSLA(ticketObject, slaPolicyObject, holidaysArray);
// → { elapsedMin, dueBy, breach, breachMin, targetMin }

const summary = computeSummary(resultsArray);
// → { prioritySummary: [...], groupSummary: [...] }
```

## Build

```bash
npm run build    # Outputs to dist/
npm run preview  # Preview the production build
```

## Tech Stack

- **Vue 3** (Options API)
- **Vite 5** (dev server + bundler)
- Pure CSS (no UI framework dependency)
- No runtime dependencies beyond Vue

## Author

Davinder Singh Bhangu