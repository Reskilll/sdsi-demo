# PROMPTS.md — AI Collaboration Record

## Project: URL Shortener with Analytics

### Initial Prompt

> "I have to create a spring backend and simple html frontend to see the shortened url on ui, the main focus should be on backend. create a simple yet working solution with all edge cases covered."

### Judging Criteria Addressed

The following criteria were given as the evaluation rubric. Here is how each was addressed:

| Criterion | Approach |
|-----------|----------|
| **M1 — Shorten (base62, 6-8 chars, custom alias, expiry)** | `Base62Encoder` converts auto-increment DB ID to base62 with 6-char minimum padding. Custom aliases accepted 4-20 chars with validation. Optional `expiryDays` stored as `expiresAt`. |
| **M2 — Resolve: 302/410/404** | Controller returns `302 FOUND` redirect for valid codes, `410 GONE` for expired, `404 NOT FOUND` for unknown. Exception hierarchy (`NotFoundException`/`GoneException`) mapped via `@ExceptionHandler`. |
| **M3 — URL validation (http/https only, reject javascript:)** | `UrlValidator` blocks a set of dangerous schemes (`javascript:`, `data:`, `file:`, `mailto:`, `ftp:`, etc.) before URI parsing, checks scheme is http/https, validates host presence, auto-prepends `https://` to bare domains. |
| **M4 — Idempotent shorten** | Service checks `findByOriginalUrlAndIsCustomAliasFalse` before creating. Re-expired old entries get a fresh lease instead of a new code. Custom alias collisions with different URLs are rejected. |
| **M5 — Stats (total clicks, per-day, last accessed)** | Each resolution writes a `ClickEvent` with timestamp. Service aggregates via: aggregate `clickCount` on `ShortenedUrl`, `lastAccessedAt` as the most recent click, and `clicksPerDay` via `GROUP BY DATE(clicked_at)`. Returned as structured JSON. |

### Additional Design Decisions

1. **Database choice**: H2 file-based DB for zero setup. The schema is JPA-managed (`ddl-auto: update`), so swapping to PostgreSQL requires only changing `application.properties`.
2. **Code generation strategy**: Base62-encoded primary key instead of random generation. Eliminates collision risk entirely while maintaining short codes.
3. **Reserved alias prefixes**: `stats`, `api`, `admin` — prevents users from squatting on routes that might be added later.
4. **Custom alias same-URL idempotency**: If the custom alias already points to the same URL, return it rather than erroring.
5. **The frontend**: Single HTML file with no build step — two tabs (Shorten/Stats), dark mode support, copy-to-clipboard. Stateless; all state is on the server.
6. **Testing strategy**: Unit tests for the two utility classes, mocked service tests for business logic, and a `@SpringBootTest` integration test that exercises the full stack through MockMvc.
7. **Security**: Input length limits everywhere (URL 2048, alias 20, headers 128/256), blocked schemes, Spring Boot's built-in CSRF protection not needed (no sessions), CORS open for the API so the frontend can be served from anywhere.
8. **Error handling**: Structured JSON error responses with status code, error type, message, and per-field validation errors. Consistent across all endpoints.

### Iterations

- **Pass 1**: Created full project structure (models, repos, service, controller, utils).
- **Pass 2**: Added comprehensive tests (unit + integration), frontend HTML, CORS config.
- **Pass 3**: Added README with API docs, architecture diagram, design decisions.

### Running the Project

```bash
mvn spring-boot:run
# Open http://localhost:8080
```

### Test Coverage

- `Base62EncoderTest` — encoding/decoding, edge cases, round-trip for large IDs
- `UrlValidatorTest` — valid URLs, blocked schemes, blank/null, length limits
- `UrlShortenerServiceTest` — shorten, idempotency, custom alias, expiry, resolve (404/410/302), stats
- `UrlShortenerIntegrationTest` — full HTTP flow: shorten → resolve → stats, idempotency, custom alias, error cases