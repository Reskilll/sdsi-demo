# PS6: IT Service-Desk SLA Tracker

Java 25 + Maven implementation that computes business-hours SLAs for service-desk tickets.

## Build & Run

```bash
cd submissions/aditya-swarnkaar
mvn -q clean package          # compiles + runs tests
java -cp target/classes:sla.gson.jar sla.Main sample/tickets.json sample/sla_policy.json sample/holidays.json
```

Or run tests only:
```bash
mvn -q test
```

Run an end-to-end example (uses `--as-of` cutoff):
```bash
java -cp target/classes:<gson> sla.Main sample/tickets.json sample/sla_policy.json sample/holidays.json --as-of 2026-01-15T18:00:00Z --output results.json
```

## CLI

```
java sla.Main <tickets.json> [sla_policy.json] [holidays.json] [--zone TZ] [--as-of ISO] [--output out.json]
```

Defaults: zone `UTC`, `--as-of` = now, output to stdout.

## Schemas

- **tickets.json**: `{ "tickets": [ { "ticket_id", "priority" (P1-P4), "assignee_group", "created_at", "status_history": [ {"status","timestamp"} ] } ] }`
- **sla_policy.json**: `{ "P1": 240, "P2": 480, "P3": 1440, "P4": 4320 }` (minutes; missing priorities get defaults)
- **holidays.json**: `[ "YYYY-MM-DD", ... ]`

Timestamps are ISO-8601 (with offset, or naive → interpreted in `--zone`).

## Assumptions & Semantics

- **Business hours**: Monday–Friday `[09:00, 18:00)` — closed at 18:00.
- **Timezone**: single configurable zone (default UTC); never mix naive/aware.
- **Holidays**: date-only strings, interpreted in the configured zone.
- **ON_HOLD**: clock pauses from first `ON_HOLD` entry to next non-`ON_HOLD` entry; ticket still on hold ⇒ hold runs to `as_of`. Multiple/overlapping holds merged.
- **Elapsed**: active business minutes in `[created, as_of)` minus hold intervals.
- **Due-by**: advance exactly `target` minutes of active business clock from `created` (skipping nights/weekends/holidays/holds) — deterministic integer math.
- **Breach**: `as_of >= due_by` (exact deadline is NOT a breach). `breach_minutes` = active minutes in `[due_by, as_of)` (0 for non-breached).
- **Unresolved tickets**: evaluated up to `as_of` (not their last status timestamp).
- **History**: sorted by timestamp; entries before creation time rejected; missing history = ticket remains `NEW`.
- **Rounding**: all minutes are floor'd integers; percentages round to 1 decimal.
- **Denominator**: per-priority summary denominator = all tickets of that priority; per-group denominator = all tickets of that group. Empty groups omitted.

## Output fields

- `elapsed_business_minutes`, `sla_target_minutes`, `due_by`, `breached`, `breach_minutes`, plus `ticket_id`, `priority`, `assignee_group`, `current_status`.