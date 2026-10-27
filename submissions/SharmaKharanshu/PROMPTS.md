# PROMPTS.md — AI Collaboration Record

## Problem
PS6: IT Service-Desk SLA Tracker — compute SLA breaches using business-hours arithmetic.

## Iterations

### Round 1 — Full scaffold
**Prompt**: "Build complete working solution with FastAPI, engine, tests, dashboard"
**Output**: All 7 files written in one shot. Engine handles M1–M5 plus edge cases.
**Learnings**:
- `_next_business_day` needs to handle `d` already being a business day → skip the +1.
- Status history should be sorted internally (defensive).
- `resolved_at` can be null → substitute `datetime.now()`.

### Round 2 — Overnight calculation bug
**Context**: `_next_business_moment` was calling `_next_business_day(d + timedelta(days=1))`, but `_next_business_day` already adds +1 day internally, causing a double-skip (2 days).
**Fix**: Pass `d` instead of `d + timedelta(days=1)`.

## Design Decisions
- **Pure engine**: No framework deps in `engine.py` → testable standalone.
- **Stateless engine**: Policy + holidays injected once → reuse across tickets.
- **FastAPI + Jinja2**: Lightweight, no build step, instant dashboard.
- **Business-minute arithmetic**: Day-by-day iteration, safe and correct.

## What Claude Did Well
- Correct business-hours logic including holiday skipping and ON_HOLD pauses.
- Comprehensive test suite covering M1–M5 and edge cases.
- Clean separation: engine (logic) / app (web) / test.
- Dark-themed dashboard without external CSS dependencies.