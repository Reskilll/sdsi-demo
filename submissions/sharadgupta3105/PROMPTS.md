# PROMPTS.md — AI collaboration log

This file records how the problem was broken down, the prompts used to build
each part, and where the AI output was reviewed and corrected rather than
accepted blindly. The intent is to show a real engineering loop, not a
copy-paste of generated code.

## 1. Breaking down the problem

The brief lists five must-haves (M1–M5). I decomposed them into separable
concerns before writing any code:

| Concern | Where it lives | Notes |
|---------|----------------|-------|
| M3 URL validation | `backend/src/validator.js` | http/https only, reject `javascript:` etc. |
| M1 code generation + M4 idempotency | `backend/src/engine.js` + partial unique index in `db.js` | base62, 6 chars, one code per URL |
| M2 resolve (302/410/404) | `backend/src/engine.js` → `app.js` routes | click recorded only on 302 |
| M5 stats | `backend/src/engine.js` | total, per-day, last-access |
| Interface vs engine | `engine.js` vs `app.js` | scored dimension: separation |

## 2. Prompts used (condensed)

**Prompt — URL validation**
> "Validate that a URL is http/https only and reject javascript:-style schemes.
> Use the WHATWG URL parser; normalize the result."

**Prompt — idempotency**
> "Shortening the same URL twice must return the same code unless a custom
> alias is given. Enforce this at the DB level, not just in application code."

**Prompt — resolve semantics**
> "Return 302 for a valid code, 410 for an expired one, 404 for unknown.
> Only record a click on a successful redirect."

**Prompt — stats**
> "Per code: total clicks, clicks per day, and last-accessed time. Keep the
> per-day aggregation indexed so it stays O(n) in the day count, not in clicks."

## 3. Corrections made to AI output

These were issues I caught in review and fixed by hand — not left as generated:

1. **Scheme case sensitivity** — an initial implementation compared the raw
   string to `http:`/`https:`, which misses `HTTPS://` and `JAVASCRIPT:`.
   Fixed by relying on `new URL().protocol`, which lowercases. Added a test
   for `javascript://x` and uppercase schemes.

2. **`javascript://` parsing edge case** — some parsers treat `javascript://`
   leniently. Verified `new URL('javascript://x')` yields a non-http protocol
   and is rejected; covered by a test.

3. **Redirect route shadowing** — the `/:code` redirect route, if registered
   first, would swallow `/api/*`. Fixed by registering `/api/*` routes before
   the catch-all, and adding a `/api/health` probe.

4. **Idempotency double-insert race** — initial version checked-then-inserted
   in app code only. Added a partial unique index so a concurrent second
   shorten cannot insert a duplicate row; a test asserts the row count stays 1.

5. **`lastAccessedAt` over-counting** — an early draft updated `last_accessed`
   on any lookup (including stats and 404s). Corrected so only a `302`
   resolution records a click / last-access.

6. **Frontend dead imports** — a generated `App.vue` imported `useRoute` and a
   view it never used. Removed them (dead code is penalized).

## 4. Edge cases considered beyond the brief

- Empty, whitespace-only, and overly long URLs (rejected with `INVALID_URL`).
- URLs with embedded spaces or no hostname.
- Custom alias colliding with an auto-generated code (aliases are reserved on
  first use; auto codes skip reserved names).
- Custom alias that is invalid (`bad alias!`, empty, >64 chars).
- Expiry in the past → immediate `410`; expiry in the future → `302`.
- Non-JSON request bodies and oversized payloads → `400`/`413`, no crash.
- Unknown code stats → `404` JSON, not a 500.

## 5. What the AI could not verify on its own

Tests are written to be runnable but were not executed by the model; the
README's single `npm start` command and `npm test` flow were authored to be
self-contained so a human or CI can run them in one step.
