# PS6: IT Service-Desk SLA Tracker

Compute SLA breaches for support tickets using business-hours-only counting that
respects holidays and ON_HOLD pauses.

## Quick-start

```bash
cd submissions/shreyasharma29119
python run.py
```

No dependencies — stdlib only (Python ≥ 3.10).

## Project structure

```
submissions/shreyasharma29119/
├── run.py                 # Entry-point script
├── sla_tracker/
│   ├── __init__.py
│   ├── models.py          # Data classes (Ticket, SlaPolicy, TicketSlaResult)
│   ├── calendar.py        # Business-hours math (M1, M2)
│   ├── sla_calculator.py  # Core SLA logic — active periods + breach calc
│   ├── reporter.py        # Tabular output + summary (M4, M5)
│   ├── cli.py             # Argument parser & orchestration
│   └── validation.py      # JSON loading & input validation
├── data/
│   ├── tickets.json       # Sample ticket data
│   ├── sla_policy.json    # SLA targets & business-hours window
│   └── holidays.json      # List of exclusion dates
├── tests/
│   └── test_sla.py        # Unit tests covering all M1–M5 requirements
├── README.md
└── PROMPTS.md
```

## Usage

```bash
# Default — uses data/ files, reference time = now
python run.py

# Custom data paths
python run.py --tickets my_tickets.json --policy my_policy.json --holidays my_holidays.json

# Set a fixed reference time for reproducible results
python run.py --reference-time "2026-10-22T18:00:00"

# JSON output for programmatic consumption
python run.py --json
```

## Input format

### `tickets.json`

```json
[
  {
    "id": "T01",
    "priority": "P1",
    "assignee_group": "Network",
    "created": "2026-10-19T09:30:00",
    "resolved": "2026-10-19T13:00:00",
    "status_history": [
      { "status": "IN_PROGRESS", "at": "2026-10-19T09:30:00" }
    ]
  }
]
```

`resolved` may be `null` for open tickets (clock runs until the reference time).
`status_history` entries with `"ON_HOLD"` pause the SLA clock for that segment.

### `sla_policy.json`

```json
{
  "priorities": {
    "P1": { "target_hours": 4 },
    "P2": { "target_hours": 8 },
    "P3": { "target_hours": 24 },
    "P4": { "target_hours": 72 }
  },
  "business_hours": {
    "days": [0, 1, 2, 3, 4],
    "start": "09:00",
    "end": "18:00"
  }
}
```

`days`: 0=Monday … 6=Sunday.

### `holidays.json`

```json
["2026-11-26"]
```

## Running tests

```bash
pip install pytest     # only if not already installed
python -m pytest tests/ -v
```

## Requirements covered

| Requirement | How it's met |
|---|---|
| **M1** SLA by priority in business hours | `calendar.py` — `business_minutes_between` and `add_business_minutes` operate on Mon–Fri 09:00–18:00 only |
| **M2** Exclude holidays | `calendar.py` accepts a `holidays: set[date]` parameter — holiday business days contribute zero minutes |
| **M3** Pause on ON_HOLD | `sla_calculator.py::_active_periods` carves out segments where status = ON_HOLD |
| **M4** Per-ticket report | `reporter.py::format_ticket_report` prints elapsed, due-by, breach flag, breach minutes |
| **M5** Summary | `reporter.py::format_summary` prints breach % per priority and per assignee group |