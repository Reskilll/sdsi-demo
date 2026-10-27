# Akhil's SLA Tracker

SLA Tracker calculates support-ticket elapsed business minutes, due-by times,
breach status, and breach minutes. It also reports breach percentages by
priority and assignee group. The implementation uses only the Python standard
library and reads JSON input files.

## Run

Requires Python 3.10 or later. From this directory:

```powershell
python sla_tracker.py
```

The report is printed as JSON. To save it to a file:

```powershell
python sla_tracker.py --output report.json
```

Active tickets are evaluated at the current time by default. Supply `--as-of`
for a reproducible report, for example:

```powershell
python sla_tracker.py --as-of 2026-10-27T12:00:00Z
```

Custom input paths can be supplied with `--tickets`, `--policy`, and
`--holidays`. All ticket timestamps and `--as-of` must include a timezone.
Calculations use the IANA timezone configured by the policy; holiday dates
refer to local dates in that timezone.

## Input format

`sla_policy.json` configures business days (`0` = Monday), local business
hours, timezone, and positive integer SLA targets in hours. The supplied policy
uses weekdays, 09:00–18:00, and targets P1=4h, P2=8h, P3=24h, P4=72h.

`holidays.json` contains a `holidays` array of `YYYY-MM-DD` dates. `tickets.json`
contains a `tickets` array. Each ticket has a unique `ticket_id`, `priority`,
`created_at`, optional `assignee_group`, optional `resolved_at` or `closed_at`,
and optional chronological `status_history` entries. Events may use
`timestamp` or `at`, and `status` or `to`; optional `from` values are checked
against the preceding status. If no `initial_status` is supplied, status
history begins in `OPEN` (or uses the first event's `from`).

An unresolved ticket is measured through `--as-of`. An open ON_HOLD interval
pauses elapsed time through that instant; its reported due-by assumes the
ticket resumes immediately at `--as-of`, since a future resume time is not
known. Elapsed and breach values are reported in whole business minutes,
rounded down. A breach is reported once elapsed business minutes exceed the
priority target.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Design and operational notes

- Business windows are intersected with ticket lifetime and hold intervals, so
  nights, weekends, holidays, and ON_HOLD time do not accrue SLA minutes.
- Input validation rejects naive timestamps, malformed policies, duplicate
  ticket IDs, and inconsistent or out-of-order status history.
- The due-by calculation advances by business windows rather than minute-by-
  minute simulation. Calculations are bounded to a 100-year horizon.
- The sample dates and holiday demonstrate the calculation; replace them with
  the operating calendar and ticket data for a real service desk.