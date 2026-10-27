# SLA Breach Computation Agent

Computes SLA breaches for support tickets against configurable targets.

## Files

| File | Purpose |
|------|---------|
| `sla_engine.py` | Core engine – all business logic |
| `main.py` | Agent entry point (matches scaffold contract) |
| `test_sla_engine.py` | Unit tests with hand-verified expected values |
| `tickets.json` | 8 sample tickets covering all priorities & edge cases |
| `sla_policy.json` | SLA targets: P1=4h, P2=8h, P3=24h, P4=72h |
| `holidays.json` | Excluded dates (2026-10-22 = holiday) |

## How it works

### M1 – Business hours only
Each priority maps to a hard target in business hours. Only Mon–Fri 09:00–18:00
counts toward SLA time. Time outside this window (evenings, weekends) does not
accrue.

### M2 – Holiday exclusion
Dates listed in `holidays.json` are treated as non-business days. No SLA time
accrues on these days, and the due-by clock skips over them.

### M3 – ON_HOLD pause
The status history is parsed to build *active intervals*. Any period where the
ticket is in `ON_HOLD` status is excluded from elapsed-time calculation. The
clock resumes when the ticket leaves `ON_HOLD`.

### M4 – Per-ticket report
Every ticket gets:
- `elapsed_business_minutes` – minutes of active SLA clock time
- `due_by` – ISO timestamp of when the SLA target expires
- `breach` – `true` if elapsed > target
- `breach_minutes` – how far past the target (0 if not breached)

### M5 – Breach summary
Grouped by priority and by assignee group, showing total tickets, breached
count, and breach percentage.

## Test cases covered

| Ticket | Priority | Scenario | Expected |
|--------|----------|----------|----------|
| TKT-001 | P1 | Same-day resolve, 3.5h | No breach |
| TKT-002 | P1 | ON_HOLD, 7.5h active | Breach |
| TKT-003 | P2 | Multi-day, 12h active | Breach |
| TKT-004 | P2 | ON_HOLD + holiday, 1h active | No breach |
| TKT-005 | P3 | Multi-day + holiday, 27h | Breach |
| TKT-006 | P3 | Still open, reentrant ON_HOLD | Ongoing |
| TKT-007 | P4 | 10-day span, 58h active | No breach |
| TKT-008 | P4 | Multi-day + holiday | No breach |

## Manual verification (key examples)

**TKT-002 (P1 breach):** Mon 10:00→ON_HOLD 11:00, Tue 09:00→15:30.
Active = 60 min + 390 min = 450 min. Target = 240 min. Breach by 210 min. ✓

**TKT-004 (P2, no breach, holiday):** ON_HOLD Mon 17:00→Thu 09:30.
Thu = holiday → only Mon 16:00–17:00 counts = 60 min < 480 min. ✓

**TKT-005 (P3 breach):** Mon/Tue/Wed full days = 3×540=1620 min.
Thu = holiday = 0. Target = 1440 min. Breach by 180 min. ✓

## Run

```bash
python main.py
```

## Test

```bash
python -m pytest test_sla_engine.py -v
```