# IT Service-Desk SLA Tracker

Enterprise-grade SLA breach calculator with business-hour calendar arithmetic, holiday exclusions, ON_HOLD pause management, and multi-dimensional reporting.

## Quickstart

```bash
# Compute SLA for all tickets and print terminal report
python main.py run

# Filter by priority or assignee group
python main.py run --priority P1
python main.py run --assignee-group "Network Ops"

# Export reports
python main.py json          # JSON (stdout)
python main.py json -o report.json
python main.py csv           # CSV (stdout)
python main.py csv -o report.csv
python main.py html          # Standalone HTML dashboard

# Generate synthetic test data
python main.py generate -n 100 --seed 42

# Performance benchmark
python main.py benchmark -n 10000 -r 5

# Run tests
python -m unittest discover -s tests -v
```

## Architecture

```
sla_tracker/
├── models.py      # Data models (Ticket, SLAPolicy, TicketSLAResult, AnalyticsSummary)
├── calendar.py    # Business hours, interval math (O(1) day blocks), holiday lookup
├── engine.py      # Core SLA calculator — timeline slicing, due-by projection
├── analytics.py   # Aggregation engine — breach % by priority & assignee group
├── validator.py   # Schema validation, timezone handling, sanitization
├── reporter.py    # Terminal (ANSI), JSON, CSV, HTML output
└── synthetic.py   # Test data generator with edge case scenarios
```

## SLA Policy

| Priority | Target (business hours) |
|----------|------------------------|
| P1       | 4 hours (240 min)      |
| P2       | 8 hours (480 min)      |
| P3       | 24 hours (1440 min)    |
| P4       | 72 hours (4320 min)    |

Business hours: Mon–Fri 09:00–18:00 (540 minutes/day). UTC-normalized with holiday exclusions.

## Edge Cases Covered

- **EC1**: Tickets created outside business hours (weekends, late night)
- **EC2**: Tickets resolved outside business hours
- **EC3**: ON_HOLD pauses spanning weekends/holidays
- **EC4**: Rapid repeated state transitions
- **EC5**: Open/in-flight ticket evaluation at a configurable `as_of` time
- **EC6**: Tickets created directly in ON_HOLD status
- **EC7**: Unassigned or missing assignee group → "Unassigned" bucket
- **EC8**: Consecutive holidays and weekends (no double-deduction)
- **EC9**: Mixed timezone ISO-8601 inputs (UTC, +05:30, naive)
- **EC10**: High-volume performance — O(1) day-block arithmetic (10k+ tickets/s)

## Verification

```bash
python -m unittest discover -s tests -v    # 82 tests passing
python main.py run                          # Full CLI report
python main.py benchmark -n 1000 -r 3      # Performance validation
```

## Dependencies

Zero external runtime dependencies — Python 3.10+ standard library only.