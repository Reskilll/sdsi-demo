# Shortly — URL Shortener with Analytics

Shorten URLs into 6-character base62 codes, resolve them, and track per-link
click analytics. Built for the SDSI developer track.

## Stack

- **Frontend** — Vue 3 (Composition API) + Vite + Vue Router
- **Backend** — Node.js + Express
- **Storage** — SQLite via `better-sqlite3` (embedded, zero-config, no external DB)
- **Tests** — Vitest

No external APIs, LLM keys, or internet access are required at runtime.

## Setup

Requires Node.js ≥ 20.

```bash
npm install
npm start          # builds the frontend, then serves everything on one port
```

Open http://localhost:3000. The single run command above is all you need;
`PORT=3000` is the default and can be overridden.

### Development

```bash
npm run dev:api     # backend on :3000
npm run dev:web     # frontend on :5173 (proxies /api to :3000)
npm test            # backend unit tests
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/shorten` | Create a short link. Body: `{ "url": "...", "customAlias"?: "...", "expiresAt"?: "ISO" | unix-seconds }` |
| `GET`  | `/api/stats/:code` | Click analytics for a code |
| `GET`  | `/:code` | Resolve: `302` redirect, `410` expired, `404` unknown |

### Response examples

**Shorten** — `201 Created` (new) or `200 OK` (idempotent hit):

```json
{ "code": "aB3xYz", "url": "https://example.com/", "shortUrl": "http://localhost:3000/aB3xYz", "created": true, "expiresAt": null }
```

**Stats**:

```json
{ "code": "aB3xYz", "url": "https://example.com/", "totalClicks": 12, "lastAccessedAt": "2026-10-27T09:00:00.000Z", "clicksPerDay": { "2026-10-27": 12 } }
```

**Errors** use a stable `error.code` plus a human `message`, with matching HTTP
status (400 validation, 409 alias taken, 404 not found, 413 too large, 500 internal).

## Assumptions

- Base62 codes are 6 characters (within the required 6–8 range).
- A custom alias is a string of `A–Z a–z 0–9 _ -`, 1–64 chars, and is never
  auto-generated (idempotency does not apply to aliases).
- Equivalent URLs normalize to one canonical form (`HTTPS://Example.com` →
  `https://example.com/`), so they share a code.
- Expiry accepts ISO 8601 or unix seconds; a past expiry is allowed and the
  link immediately resolves to `410`.
- `lastAccessedAt` is only set by a *successful* redirect (a `302`), not by
  `404`/`410` lookups or stats views.

## Design choices

- **Engine / interface separation** — [`backend/src/engine.js`](backend/src/engine.js)
  holds all logic (shorten, resolve, stats, idempotency); [`backend/src/app.js`](backend/src/app.js)
  is a thin Express layer that only maps HTTP ↔ engine and shapes errors.
  [`backend/src/validator.js`](backend/src/validator.js) isolates URL validation,
  and [`backend/src/db.js`](backend/src/db.js) the storage schema.
- **Idempotency** — a partial `UNIQUE` index on `links(url) WHERE is_custom = 0`
  guarantees one code per URL at the database level, not just in app logic.
- **Click tracking** — a `clicks` table with a `(link_id, clicked_at)` index
  makes total / per-day / last-access queries cheap (no O(n) rescans per request).
- **Concurrency** — SQLite WAL mode + synchronous `better-sqlite3` calls give
  correct, race-free reads/writes in a single Node process.

## Known gaps

- Codes are random and not recoverable by the original URL via a public
  endpoint (a "look up my code" feature) — out of scope.
- No per-click metadata (referrer, IP, user-agent) is stored; only aggregate
  counts and dates.
- No rate limiting or authentication on the API; it is a demo, not a public service.
- `expiresAt` from the browser datetime-local input is sent in local time and
  parsed server-side; UTC is recommended for API callers.

## Project layout

```
submissions/sharadgupta3105/
├── backend/
│   ├── src/           # validator, db, engine, app, server
│   └── test/          # Vitest unit tests for the engine + validator
├── frontend/          # Vue 3 SPA (shorten + analytics views)
├── package.json       # npm workspaces root
├── README.md
└── PROMPTS.md
```
