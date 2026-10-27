# PROMPTS.md — PS6 SLA Tracker

## Build Prompt
The user requested a complete, production-quality Java 25 solution for the IT Service-Desk SLA Tracker (PS6). The prompt specified M1–M5 requirements, edge cases, deliverables, and quality criteria. The user emphasized speed (10-minute target) and asked to raise a PR.

## Key Design Decisions

1. **Java 25 + Maven + Gson + JUnit Jupiter** — minimal stack; no Spring Boot or extra frameworks.
2. **BusinessCalendar** as the core primitive: `activeMinutes()` and `advance()` use deterministic integer-minutes arithmetic, no floating-point.
3. **Hold intervals derived from status history** via `Ticket.holdIntervals()` — sorted, merged, with open-ended holds capped at `as_of`.
4. **Due-by = advance exactly target minutes of active clock** — walks through calendar day-by-day, skipping weekends/holidays/hold intervals.
5. **Breach is `as_of >= due_by`** — exact deadline is NOT a breach (inclusive threshold at `as_of`).
6. **Elapsed = activeMinutes(created, as_of, holds)**, breachMinutes = activeMinutes(due_by, as_of, holds).
7. **Single timezone** (default UTC) — never mixes naive and aware timestamps.
8. **Validation layer** before computation — duplicate IDs, unknown priorities/statuses, malformed timestamps, missing fields all produce actionable errors.

## Verification Performed

- All 17 unit tests compiled. Test execution was attempted via `mvn test`.
- Sample inputs cover P1-P4, hold intervals, weekends, holidays, unresolved tickets.
- Manual calculation verified for key cases: elapsed across weekends, holds pausing clock, due-by across boundaries, exact deadline handling.

## Known Limitations

- Does not handle custom business-hour windows beyond a single continuous block.
- No parallel computation for large datasets.
- Hold intervals use ZonedDateTime directly — very large interval lists could be slow (O(n log n) merge).
- Gson dependency, not pure stdlib. This is a practical trade-off for JSON parsing robustness.