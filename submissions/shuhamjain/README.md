# PS3: URL Shortener with Analytics

Shorten URLs into short base62 codes, resolve them with correct HTTP
semantics (302 / 410 / 404), and track per-link usage analytics.

- **Backend:** Node.js 20+ (no TypeScript) + Fastify + built-in `node:sqlite`
- **Frontend:** Vue 2 + Vue CLI (analytics dashboard)
- **Tests:** Node's built-in `node --test` runner (no extra test framework)

> **Requirement:** Node.js **22.x** or later. The backend uses the built-in
> `node:sqlite` module (no native compilation, no Python/build tools needed).

---

## Quick start

### Backend

```bash
cd backend
npm install
npm test        # 19 tests — unit + integration
npm start       # serves on http://127.0.0.1:3000 (override PORT / HOST via env)
```

### Frontend (optional dashboard)

```bash
cd frontend
npm install
npm run serve   # dev server on http://localhost:8080, proxies /api to :3000
```

Run the backend first, then the frontend, and open http://localhost:8080.

---

## API

| Method | Path | Body / params | Success | Errors |
|--------|------|---------------|---------|--------|
| `POST` | `/api/shorten` | `{ "url": "https://...", "alias": "opt", "ttl": 3600 }` | `200` `{ code, shortUrl, originalUrl, custom, expiresAt, createdAt }` | `400` invalid URL/scheme/alias/ttl, `409` alias taken, `429` rate limited |
| `GET` | `/:code` | — | `302` redirect to original URL | `404` unknown code, `410` expired |
| `GET` | `/api/stats/:code` | — | `200` `{ code, originalUrl, totalClicks, clicksPerDay, lastAccessedAt, ... }` | `404` unknown code |
| `GET` | `/healthz` | — | `200` `{ "ok": true }` | — |

### `curl` examples

```bash
# Shorten
curl -s -X POST http://127.0.0.1:3000/api/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/some/long/path"}'
# → {"code":"100000","shortUrl":"http://127.0.0.1:3000/100000",...}

# Shorten with a custom alias + 1-hour expiry
curl -s -X POST http://127.0.0.1:3000/api/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/x","alias":"my-link","ttl":3600}'

# Resolve (follow the redirect)
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://127.0.0.1:3000/100000

# Stats
curl -s http://127.0.0.1:3000/api/stats/100000
```

---

## Design decisions (summary)

- **base62 codes from a counter** starting at `62^5`, so codes are always
  6–8 chars and collisions are impossible by construction (no retry loop).
- **Idempotency (M4):** a canonical form of each URL is hashed; shortening the
  same URL returns the same code, unless a custom alias is supplied.
- **Validation (M3):** `new URL()` parse + strict **http/https** allowlist
  (rejects `javascript:`, `data:`, `file:`, `ftp:`, …), plus canonicalization
  (lowercase host, strip default port/fragment).
- **Resolution (M2):** `302` (not `301`, so browsers don't cache away future
  clicks), `410` when expired, `404` when unknown.
- **Analytics (M5):** one row per `(link, day)` upserted per click; stats derive
  total + per-day counts and `lastAccessedAt`.
- **Security:** parameterized SQL, self-host/redirect-loop rejection, rate
  limiting on `/api/shorten`, reserved-alias blocklist, no stack traces leaked.

See `solution.md` for the full rationale and `PROMPTS.md` for the AI
collaboration log.

---

## Project layout

```
submissions/shuhamjain/
├── problem.md        # given problem statement
├── solution.md       # design approach + stack rationale
├── README.md         # this file
├── PROMPTS.md        # AI collaboration log
├── backend/          # Node 22 + Fastify + node:sqlite
│   ├── src/
│   │   ├── server.js        # app assembly, rate limiting, error handler
│   │   ├── routes.js        # HTTP routes
│   │   ├── db.js            # schema + migrations
│   │   ├── services/        # shorten / resolve / stats
│   │   └── lib/             # base62, url canonicalization, errors
│   └── test/                # unit + integration tests
└── frontend/         # Vue 2 analytics dashboard
```