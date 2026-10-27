# PS3: URL Shortener with Analytics — Solution Approach

## Problem summary
Shorten long URLs into short base62 codes (6–8 chars), resolve them with the
correct HTTP semantics (302 / 410 / 404), and track per-link usage analytics.
The same URL must shorten to the same code on repeat (idempotent) unless a
custom alias is requested.

The five scored milestones map cleanly onto a small HTTP API:

| Milestone | Requirement |
|-----------|-------------|
| M1 | Shorten a URL → base62 code of 6–8 chars (optional custom alias + expiry) |
| M2 | Resolve a code → 302 redirect, 410 Gone if expired, 404 if unknown |
| M3 | URL validation: http/https only, reject malformed URLs and `javascript:`-style schemes |
| M4 | Idempotent shortening (same URL → same code), except when a custom alias is given |
| M5 | Per-code stats: total clicks, clicks per day, last accessed time |

---

## Recommended stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | **Node.js (v20+ LTS) + plain JavaScript + Fastify** | Node is the right call for an I/O-bound redirect service. Fastify gives built-in request/response schema validation (helps M3, security, and input-validation judging) and better throughput than Express with almost no learning curve. Plain JS keeps setup minimal; the module boundaries are kept clean so types could be added later if desired. |
| Database | **SQLite via `better-sqlite3`** | Zero-config, single file, fully *runnable* by the evaluator with no external service. Unique indexes give us idempotency + collision safety. The schema is portable to Postgres if scale matters later. |
| Frontend | **Vue 2 + Vue CLI** | The analytics dashboard is a *stretch/bonus*, not a scored milestone. Vue 2 is chosen per the author's preference and experience. Note: Vue 2 reached end-of-life at the end of 2023 (no further security patches) — chosen knowingly for this demo; the code is kept framework-light so migrating to Vue 3 later is straightforward. |
| Tests | **Jest + Supertest** | Same language as the backend, fast, covers unit + integration. |

*Build the backend first (that's what's scored); the dashboard is a bonus we add
after M1–M5 are green.*

---

## Architecture

Three small modules, one process:

```
client ──> /api/shorten ──> ShortenService ──> [links] table
client ──> /:code      ──> ResolveService ──> [links] + [clicks] tables
client ──> /api/stats/:code ──> StatsService ──> aggregate [clicks]
                              └─> optional Vue dashboard on the same host
```

### Data model

```sql
-- links: one row per (URL, code) pair
CREATE TABLE links (
  id             INTEGER PRIMARY KEY,
  url            TEXT NOT NULL,          -- canonical form (see below)
  url_hash       TEXT NOT NULL,          -- sha256(url), indexed (not unique!)
  code           TEXT NOT NULL UNIQUE,   -- base62, or the custom alias
  custom         INTEGER NOT NULL DEFAULT 0,  -- 1 = user-supplied alias
  expires_at     INTEGER,                -- unix millis, NULL = never
  created_at     INTEGER NOT NULL,
  last_accessed_at INTEGER
);

-- clicks: one row per (link, calendar-day), upserted
CREATE TABLE clicks (
  link_id INTEGER NOT NULL,
  day     TEXT    NOT NULL,              -- 'YYYY-MM-DD' (UTC)
  count   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (link_id, day)
);
```

`url_hash` is deliberately **not** unique so a URL can have both its idempotent
auto-code *and* any number of custom aliases (M4 allows that).

---

## Key design decisions

### 1. URL validation & normalization (M3)
Validate on input, only after normalizing:

1. Parse with `new URL()`. Anything that throws, or has no hostname → reject 400.
2. **Scheme allowlist**: accept only `http:` / `https:`. This kills `javascript:`,
   `data:`, `ftp:`, `file:` etc. in one check (defense in depth: still check the
   scheme before ever trusting user input).
3. Reject `about:`, `blob:`, and any `\0` / control chars.

Then normalize to a canonical key so idempotency works (M4):
- lowercase the scheme + hostname
- strip the default port (`:80`/`:443`)
- remove the fragment (`#...`)
- drop a trailing `/` only when path is empty
- (optional) convert internationalized domains to punycode via `URL`'s own parser

**Why:** `http://EXAMPLE.com:80#x` and `http://example.com` must hash identically,
otherwise M4 fails in the common cases evaluators will try.

### 2. Code generation — counter-based base62 (M1)
Encode a monotonically increasing integer as base62 using an alphabet of
`0-9A-Za-z`. Start the counter at `62^5 = 916,132,832` so every generated code
is **exactly 6 or more** chars and stays within the 6–8 window for the first
~35 billion links. Store the counter in a single-row table and increment inside
a transaction so codes are collision-free by construction (no retry loop).

Alternative (random 6-char + collision retry) is simpler but needs a retry loop
under the unique index; the counter is deterministic and tidier under load.

Custom aliases: validate against `/^[A-Za-z0-9_-]{1,32}$/`, reject a small
reserved list (`api`, `stats`, `health`, …), and let the `UNIQUE` index on `code`
return 409 Conflict if taken. Also reject aliases that could collide with a
future auto-code pattern if we want to be extra safe.

### 3. Idempotency (M4)
For a request **without** `alias`:
- compute `url_hash` of the canonical URL
- `SELECT ... WHERE url_hash = ? AND custom = 0` → if found, return the existing
  code (200, unchanged) — this is the idempotent path.
- otherwise INSERT a new row with a fresh counter code.

For a request **with** `alias`: always create that specific mapping; if the alias
is taken, 409. A race between two identical creates is handled by the unique
`code`/lookup + `INSERT OR IGNORE` (or catch the unique-constraint error and
re-read), so concurrent identical requests converge on one code.

### 4. Resolution semantics (M2)
`GET /:code` → look up by `code`:

- not found → **404**
- found but `expires_at < now` → **410 Gone** (do not redirect)
- else → **302 Found** with a single `Location` header, and record the click

**Why 302 not 301:** 301 is permanently cached by browsers, which would hide
subsequent clicks (and future expiry/analytics) from us. 302 preserves
analytics and lets expiry remain effective.

### 5. Expiry (M1/M2)
`expires_at` stored as unix millis (NULL = never). Expiry is checked at resolve
time, not by a background janitor — the check is cheap and avoids a scheduler.
A lazy janitor (optional) can delete expired rows on a timer, but it's not needed
for correctness.

### 6. Analytics (M5)
On each successful resolve, upsert:
```sql
INSERT INTO clicks(link_id, day, count) VALUES(?, ?, 1)
  ON CONFLICT(link_id, day) DO UPDATE SET count = count + 1;
```
and set `links.last_accessed_at = now`.

`GET /api/stats/:code` returns:
- `totalClicks` = `SUM(count)`
- `clicksPerDay` = `[{day, count}...]` ordered by day
- `lastAccessedAt`, `expiresAt`, `createdAt`, `originalUrl`

**Perf note:** record the click *after* sending the redirect (or fire-and-forget
in the same process) so the client's redirect latency is never blocked on a disk
write. For this scale SQLite is more than enough; note Postgres as the swap-in
if this were to go multi-instance.

---

## API surface

| Method | Path | Success | Failure |
|--------|------|---------|---------|
| POST | `/api/shorten` `{url, alias?, ttl?}` | 200 `{code, shortUrl, originalUrl, expiresAt}` | 400 invalid URL/scheme/alias, 409 alias taken, 422 bad TTL |
| GET | `/:code` | 302 to original | 404 unknown, 410 expired |
| GET | `/api/stats/:code` | 200 stats JSON | 404 unknown |
| GET | `/healthz` | 200 | — |

(Dashboard pages under `/` are a stretch and served by the same app.)

---

## Edge cases & security (things not on the list)
- **Scheme bypass** beyond `javascript:` — `data:`, `vbscript:`, `file:` all
  blocked by the http/https allowlist.
- **Open redirect / resolving to the shortener itself** — refuse to shorten URLs
  whose host is our own host, to avoid redirect loops.
- **Unicode / IDN** — normalized to ASCII punycode before hashing.
- **Very long URLs** — cap input at e.g. 2048 chars; malformed/oversized → 400,
  never a 500.
- **Case sensitivity** — codes are case-sensitive (base62 includes `A–Z`/`a–z`);
  document this clearly.
- **Reserved / profane / short codes** — reserved prefix list for custom aliases.
- **Mass abuse / enumeration** — lightweight per-IP rate limit on `/api/shorten`.
- **SQL injection** — parameterized statements everywhere; never build SQL from
  user input.
- **Error handling** — uniform JSON error shape; no stack traces leaked; 404 vs
  410 vs 400 always returned deliberately, not accidentally.
- **Concurrent same-URL request** — handled by unique index + idempotent lookup.

---

## Testing strategy
- **Unit:** base62 encode/decode round-trip + length bounds; URL validator
  (accept `http`, `https`, valid-but-weird hosts; reject `javascript:`, `data:`,
  malformed, empty); canonicalization rules; expiry boundary (`now-1ms` → 410,
  `now+1ms` → 302); stats aggregation.
- **Integration (Supertest against the running app):**
  - shorten → resolve → 302 with correct `Location`
  - same URL twice → identical code (idempotent), custom alias → different row
  - unknown code → 404; expired code → 410
  - stats increments across resolves and counts days correctly
  - alias collision → 409; invalid input → 400
- **Edge-case table** covering the extra cases above.

---

## Deliverables & repo layout (under `submissions/shuhamjain/`)
```
problem.md        (given)
solution.md       (this file)
README.md         run instructions: install, test, run, curl examples
PROMPTS.md        AI collaboration log — the prompts used to build this (judged)
backend/          Node (JS) + Fastify app (src/, tests/)
frontend/         Vue 2 dashboard (analytics UI)
```

---

## Build order
1. Backend skeleton + validation (M3) + canonicalization
2. Shorten path with counter base62 + idempotency (M1, M4)
3. Resolve path with 302/410/404 + click recording (M2)
4. Stats endpoint (M5)
5. Tests for all milestones + edge cases
6. Vue 2 dashboard / README / PROMPTS.md polish

*Final stack confirmed:* **Node.js (plain JS) + Fastify + SQLite backend,
Vue 2 dashboard frontend.**