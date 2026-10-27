# IT Service-Desk SLA Tracker

Compute SLA breaches for support tickets using business-hours arithmetic.

## Quick Start

```bash
cd submissions/SharmaKharanshu

# Install deps (only if not already installed)
pip install fastapi uvicorn jinja2

# Run tests
python -m pytest test_engine.py -v

# Start web dashboard
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Then open **http://127.0.0.1:8000** for the dashboard, or hit the API endpoints:

| Endpoint | Description |
|---|---|
| `GET /` | HTML dashboard |
| `GET /api/report` | JSON: per-ticket SLA reports |
| `GET /api/summary` | JSON: breach % by priority & group |
| `GET /api/ticket/{id}` | JSON: single ticket report |

## Data Files (`data/`)

| File | Purpose |
|---|---|
| `tickets.json` | Support tickets with status history |
| `sla_policy.json` | SLA targets, business hours definition |
| `holidays.json` | Dates excluded from SLA clock |

## SLA Rules

| Priority | Target | Label |
|---|---|---|
| P1 | 4 business hours | Critical |
| P2 | 8 business hours | High |
| P3 | 24 business hours | Medium |
| P4 | 72 business hours | Low |

- **Business hours**: Mon–Fri, 09:00–18:00
- **Holidays**: excluded from SLA clock
- **ON_HOLD**: pauses the SLA clock
- **Breach**: `elapsed_business_minutes > sla_target`

## Project Structure

```
submissions/SharmaKharanshu/
├── app.py              # FastAPI web app
├── engine.py           # SLA calculation engine (pure logic)
├── test_engine.py      # Pytest test suite
├── data/
│   ├── tickets.json    # Sample ticket data
│   ├── sla_policy.json # SLA policy configuration
│   └── holidays.json   # Holiday calendar
├── templates/
│   └── dashboard.html  # Dashboard template
└── README.md
```

## Edge Cases Handled

- Tickets created outside business hours (clock starts at 09:00)
- Tickets resolved outside business hours (clock stops at 18:00)
- Multiple ON_HOLD periods
- Unresolved tickets (uses current time)
- Weekends and holidays skipped
- Invalid/missing priority → error
- Empty status history → 0 elapsed
- Unsorted status history → sorted internally