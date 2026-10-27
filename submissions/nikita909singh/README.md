# PS6: IT Service-Desk SLA Tracker

A command-line tool that works out SLA breaches for support tickets. It counts **business hours
only**, skips **holidays**, pauses the clock while a ticket is **ON_HOLD**, and reports each ticket's
elapsed business minutes, due-by time and breach, plus breach % per priority and per assignee group.

📋 **[Test report](TEST_REPORT.md):** 84/84 automated tests. Every ticket in the sample data is checked
against a hand-calculated answer.

- Java 21+ · Maven · Jackson (JSON) · JUnit 5 · `java.time` for time zones and daylight saving

## Requirements coverage

| # | Requirement | How |
|---|---|---|
| M1 | Targets by priority (P1 4h, P2 8h, P3 24h, P4 72h) in business hours, Mon–Fri 09:00–18:00 | [`BusinessCalendar`](src/main/java/com/sdsi/sla/core/BusinessCalendar.java), [`data/sla_policy.json`](data/sla_policy.json); also the built-in defaults |
| M2 | Holidays excluded | [`data/holidays.json`](data/holidays.json); holidays are treated as non-working days |
| M3 | Clock paused while ON_HOLD | [`SlaEngine`](src/main/java/com/sdsi/sla/core/SlaEngine.java) replays each ticket's status history |
| M4 | Per ticket: elapsed business minutes, due-by, breach yes/no, breach minutes | Text table, `--json` or `--csv` |
| M5 | Breach % per priority and per assignee group | Summary section (plus overall) |

Extras:
- `--as-of` time travel, to see the report as it stood at any moment.
- A state per ticket: MET, BREACHED, ON_TRACK, **AT_RISK** (less than 25% of the time left) or PAUSED.
- Reopened tickets resume their clock.
- JSON and CSV output; the CSV is protected against spreadsheet formula injection.
- Configurable working days, hours, time zone, status names and targets.
- Correct across daylight-saving changes.
- Every input error reported at once, with the ticket's position in the file.

## Quick start

```bash
cd submissions/nikita909singh
mvn test                    # 84 tests
mvn package -DskipTests     # builds target/sla-tracker.jar
java -jar target/sla-tracker.jar report --tickets data/tickets.json \
     --policy data/sla_policy.json --holidays data/holidays.json --as-of 2026-10-16T18:00
```

> **Windows note.** If Maven fails with `PKIX path building failed` (a proxy or antivirus intercepting
> TLS), set `MAVEN_OPTS="-Djavax.net.ssl.trustStoreType=Windows-ROOT"`.

### Sample output

```
SLA report as of 2026-10-16 18:00 Asia/Kolkata: 10 ticket(s)

TICKETS (minutes are business minutes)
  Ticket Pri  Group        Status       Target  Elapsed  Due by           Breach    Over  State
  T-1001 P1   Network      RESOLVED        240      180  2026-10-05 14:00 no           0  MET
  T-1002 P1   Network      RESOLVED        240      300  2026-10-05 11:00 YES         60  BREACHED
  T-1003 P2   Service Desk RESOLVED        480      240  2026-10-09 12:00 no           0  MET
  T-1004 P3   Applications IN_PROGRESS    1440     2940  2026-10-14 11:00 YES       1500  BREACHED
  T-1005 P4   Applications ON_HOLD        4320      720  (paused)         no           0  PAUSED
  T-1006 P2   Service Desk OPEN            480      420  2026-10-19 10:00 no           0  AT_RISK
  T-1007 P3   Network      CLOSED         1440      900  2026-10-16 16:00 no           0  MET
  T-1008 P1   Service Desk RESOLVED        240      210  2026-10-12 13:00 no           0  MET
  T-1009 P2   Network      REOPENED        480      330  2026-10-19 11:30 no           0  ON_TRACK
  T-1010 P4   Unassigned   OPEN           4320      540  2026-10-28 18:00 no           0  ON_TRACK

BREACH % BY PRIORITY
  P1                     3 ticket(s),   1 breached,   0 open    33.33% breached
  P2                     3 ticket(s),   0 breached,   2 open     0.00% breached
  P3                     2 ticket(s),   1 breached,   1 open    50.00% breached
  P4                     2 ticket(s),   0 breached,   2 open     0.00% breached

BREACH % BY ASSIGNEE GROUP
  Applications           2 ticket(s),   1 breached,   2 open    50.00% breached
  Network                4 ticket(s),   1 breached,   1 open    25.00% breached
  Service Desk           3 ticket(s),   0 breached,   1 open     0.00% breached
  Unassigned             1 ticket(s),   0 breached,   1 open     0.00% breached

OVERALL
  ALL                   10 ticket(s),   2 breached,   5 open    20.00% breached
```

Each sample ticket shows one rule. For example, T-1002 was raised Thursday 16:00, just before the
Friday 2 October holiday and a weekend, so only Thursday 16:00–18:00 and Monday 09:00–12:00 count.
T-1008 was raised on a Saturday, so its clock starts on Monday at 09:00.

## Commands

```
report   --tickets FILE [--policy FILE] [--holidays FILE] [--as-of TIME] [--json | --csv] [--skip-invalid]
validate --tickets FILE [--policy FILE] [--holidays FILE]
```

| Option | Default |
|---|---|
| `--policy` | Built in: P1 4h, P2 8h, P3 24h, P4 72h, Mon–Fri 09:00–18:00, `Asia/Kolkata` |
| `--holidays` | None |
| `--as-of` | Now. Accepts `2026-10-16T18:00` (policy time zone) or `2026-10-16T18:00+05:30` |
| `--skip-invalid` | Off: any invalid ticket stops the report, so a wrong total is never printed silently |

Exit codes: `0` OK, `1` invalid data, `2` bad command line.

## Input files

**`tickets.json`**: an object with a `tickets` array, a bare array, or a single ticket.

```json
{ "id": "T-1003", "title": "Laptop replacement", "priority": "P2", "assigneeGroup": "Service Desk",
  "createdAt": "2026-10-06T17:00:00+05:30",
  "statusHistory": [
    { "status": "ON_HOLD",     "at": "2026-10-07T10:00:00+05:30" },
    { "status": "IN_PROGRESS", "at": "2026-10-08T15:00:00+05:30" },
    { "status": "RESOLVED",    "at": "2026-10-08T17:00:00+05:30" } ] }
```

- Times are ISO-8601. Without an offset they are read in the policy's time zone.
- `statusHistory` can be in any order; it's sorted by time. A missing `assigneeGroup` becomes
  `Unassigned`.
- Status names are case-insensitive: `on hold`, `On-Hold` and `ON_HOLD` are the same.

**`sla_policy.json`**: every field is optional and falls back to the defaults.

```json
{ "timezone": "Asia/Kolkata",
  "businessHours": { "days": ["MON","TUE","WED","THU","FRI"], "start": "09:00", "end": "18:00" },
  "targetsHours": { "P1": 4, "P2": 8, "P3": 24, "P4": 72 },
  "statuses": { "running": ["NEW","OPEN","ASSIGNED","IN_PROGRESS","REOPENED"],
                "paused": ["ON_HOLD"], "stopped": ["RESOLVED","CLOSED"] },
  "atRiskFraction": 0.25 }
```

**`holidays.json`**: `{"holidays": [{"date": "2026-10-02", "name": "Gandhi Jayanti"}]}`, or a bare
array of `"YYYY-MM-DD"` strings.

## How the SLA clock works

```
created ──running──► ON_HOLD ──paused──► IN_PROGRESS ──running──► RESOLVED (stop)
                                                                     │
                                         REOPENED ◄──────────────────┘ (clock resumes)
```

1. The clock starts at `createdAt` and runs in *running* statuses, pauses in *paused* statuses and
   stops in *stopped* statuses. A reopened ticket carries on from where it stopped.
2. Only time inside business hours on working days that are not holidays counts.
3. **Elapsed** is the business time the clock ran, up to `--as-of` for open tickets. Status changes
   after `--as-of` are ignored.
4. **Due-by** is the moment the elapsed time reaches the target. If that hasn't happened yet, it's
   projected forward from now (open tickets) or from resolution (resolved tickets), assuming no
   further holds. For a ticket that is on hold and not yet late, due-by is shown as `(paused)`,
   because it depends on when work resumes.
5. **Breached** means elapsed is strictly greater than the target, so resolving exactly on time is not
   a breach. **Breach minutes** are rounded up, so a breach of a few seconds shows as 1, not 0.
6. If the target is used up exactly at 18:00, due-by is 18:00, not the next morning at 09:00.
7. **Breach %** is breached tickets ÷ all tickets in the group, open ones included. The summary also
   shows how many are still open, so a low % on mostly open tickets doesn't mislead.

## Design

```
cli/Main ─► io/InputLoader (policy, holidays, tickets: validation)
        ─► core/SlaEngine ─► core/BusinessCalendar (business-time arithmetic)
        ─► io/ReportWriter (text | JSON | CSV)
```

- `BusinessCalendar` does all the time arithmetic. It has two operations: `businessSeconds(from, to)`
  and `addBusinessSeconds(from, n)`. Each day's window is built with
  `LocalDate.atTime(...).atZone(zone)`, so daylight-saving shifts are handled by `java.time`. It works
  in seconds, so nothing is lost to rounding until the final report.
- `SlaEngine` replays the status history once per ticket. It knows nothing about JSON or output.
- Records (`Ticket`, `TicketResult`, `Summary`) are immutable.

### Performance

- Each ticket costs O(status changes + calendar days spanned). A ticket open for three years is about
  1,100 cheap day steps, and the tests run 1,000 of those well within the time limit.
- 20,000 tickets (a 4.8 MB file) take about 1.3 s on top of JVM startup.
- The holiday lookup is a hash set, O(1).

## Security and robustness

- Input files are untrusted. Their size (50 MB), nesting depth, string and number lengths are capped,
  duplicate JSON keys and unknown fields are rejected, and ids and group names use allow-list
  patterns.
- **CSV injection is prevented.** A cell starting with `=`, `+`, `-` or `@` gets a leading apostrophe,
  so opening the CSV in Excel can't run a formula.
- No runaway loops: a due-by search gives up after 10 years with a clear error. That covers a policy
  whose holidays block every working day.
- The policy itself is checked: start must be before end, at least one working day, every target
  positive and in whole minutes, a status in only one list, and a real time zone.

## Tests (84)

| Suite | Covers |
|---|---|
| `BusinessCalendarTest` | Same day, before/after hours, overnight, weekends, holidays, full weeks, seconds, adding time across weekends/holidays, the 18:00 boundary, DST (New York), custom work week |
| `SlaEngineTest` | **All 10 sample tickets against hand-calculated answers**; exactly-on-time, 1 second late, holds over weekends, several holds plus reopen, breach while on hold, as-of filtering, created after as-of, custom status names, summary %, performance |
| `InputLoaderTest` | Defaults, partial policies, 14 bad-policy cases, holiday formats, ticket shapes, local times, status normalisation, sorting, duplicate ids, every ticket rule |
| `MainTest` | Text, JSON and CSV output, as-of defaulting to now, validate, strict vs `--skip-invalid`, built-in defaults, bad command lines |
