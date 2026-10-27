# AI-Assisted Development Process

This document records the prompts and iterative process used to build the SLA Tracker.

---

## Initial Project Generation Prompt

The project was generated using the comprehensive PS6 assignment specification provided by SDSI Reskill. The full prompt included detailed requirements for:

- Technology stack (Next.js, TypeScript, MongoDB, Tailwind CSS)
- Project architecture and module separation
- Admin authentication with JWT/bcrypt
- SLA calculation engine (the most critical component)
- Frontend pages and dashboard
- API routes and validation
- Testing requirements
- Documentation

**Approach:** The AI agent implemented the project in phases, creating the project scaffold, core libraries, models, services, frontend, and tests.

---

## SLA Calculation Engine Prompts

### Initial implementation prompt:

```
Implement the SLA calculation in a dedicated, reusable, thoroughly tested TypeScript service.
The calculation must follow these rules:

M1: SLA Targets — P1=4h, P2=8h, P3=24h, P4=72h (business hours)
M2: Business Calendar — Mon-Fri, 09:00-18:00, exclude weekends and holidays
M3: ON_HOLD pauses SLA — use statusHistory to track pause/resume cycles
M4: Per-ticket results — elapsedBusinessMinutes, dueBy, isBreached, breachMinutes, slaStatus
```

**What was accepted:** The business-minute accumulation approach with minute-by-minute iteration, the hold-interval extraction from statusHistory, and the dueBy extension by hold real-time duration.

**What was modified:** Added safety caps for infinite-loop protection in `nextBusinessStart` and `addBusinessMinutes`. Added handling for empty history, invalid priority, and zero-duration tickets.

**What was rejected:** A "working-day" based approach that assumed fixed number of business days per month. This was rejected because it could not handle arbitrary holiday schedules.

---

## Edge Case Test Design Prompts

### Prompt:

```
Write automated tests covering these scenarios:
- P1 within SLA, P1 breached
- Created before 09:00, exactly at 09:00, at 18:00+
- Crossing overnight, crossing Friday to Monday
- Single and multiple ON_HOLD intervals
- Currently on hold (PAUSED status)
- Resolved exactly at deadline (not breached)
- Zero-duration tickets
- Missing/invalid inputs
- Holiday exclusion
- Custom policy overrides
```

**What was accepted:** All 20+ test cases covering the required scenarios and edge cases.

**What was modified:** Fixed the timezone offset calculations in test expectations. Several tests needed adjustment because the Asia/Kolkata timezone (UTC+5:30) created non-obvious UTC time mappings.

---

## Debugging and Refactoring Prompts

### Status transition rules:

```
Define VALID_TRANSITIONS and implement validation:
- OPEN -> IN_PROGRESS, ON_HOLD, RESOLVED
- IN_PROGRESS -> ON_HOLD, RESOLVED, OPEN
- ON_HOLD -> IN_PROGRESS, RESOLVED, OPEN
- RESOLVED -> (none)
```

**What was accepted:** The transition map approach was clean and easily testable.

### API response standardization:

Created a consistent `ApiResponse<T>` type with helpers for success, validation error, unauthorized, not found, and server error responses. This was applied across all route handlers.

---

## Security Review Prompt

```
Follow secure development practices:
- Server-only access to secrets
- Password hashing with bcrypt
- JWT session management with HTTP-only cookies
- Joi validation for all inputs
- Rate limiting on login
- Generic authentication errors
- No sensitive data in API responses
```

**What was implemented:**
- bcrypt with 12 salt rounds for password hashing
- jose library for JWT (not jsonwebtoken, as jose works better in Edge runtime)
- In-memory rate limiter on login endpoint
- Generic "Invalid email or password" error
- `select: false` on passwordHash in Admin model
- No `NEXT_PUBLIC_*` variables for secrets
- Input validation via Joi on every endpoint
- `serverExternalPackages` config for mongoose and bcryptjs

---

## Performance Review Prompt

```
Avoid N+1 queries, add database indexes, handle concurrent updates safely.
```

**What was implemented:**
- Compound indexes on Ticket model for common query patterns
- `Promise.all` for parallel database queries in dashboard/reports
- `findOneAndUpdate` for atomic status changes with `$push` to statusHistory
- Connection pooling via Mongoose (maxPoolSize: 10)
- `lean()` for read-only queries

---

## Changes from AI Suggestions

| Suggestion | Decision | Reason |
|---|---|---|
| Use jsonwebtoken | **Rejected** | jose works better with Next.js Edge runtime and has native Web Crypto |
| Use NextAuth.js | **Rejected** | Overkill for single-admin; custom JWT is simpler and meets requirements |
| Add real-time polling for dashboard | **Rejected** | Not required; user can refresh manually |
| Add Redis for rate limiting | **Rejected** | In-memory Map is sufficient for development; production can add Redis |
| Use shadcn/ui component library | **Rejected** | Avoids extra dependency; custom Tailwind components are maintainable |
| Store SLA results in database | **Rejected** | Spec says calculate live; avoids invalidation complexity |
| Use react-chartjs-2 for charts | **Rejected** | Custom CSS progress bars are simpler and meet the visual requirement |