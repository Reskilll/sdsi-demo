# AI Collaboration Notes

## Prompt used

"Implement a Python solution for PS6: compute SLA elapsed time in business
hours for P1/P2/P3/P4 tickets, exclude weekends and configured holidays, pause
the clock during ON_HOLD status intervals, report due-by and breach metrics,
and summarize breach percentages by priority and assignee group. Include sample
JSON inputs, tests, validation, and run documentation."

## Decisions reviewed

- Used an explicit policy timezone so business-day and holiday boundaries are
  unambiguous.
- Active tickets use a supplied `--as-of` time or the current time. An active
  ON_HOLD ticket's due-by assumes it resumes at the evaluation time.
- Breach status and breach minutes use whole elapsed business minutes, rounded
  down; a ticket breaches when that value exceeds its target.
- Used only the Python standard library to keep setup and execution simple.

## Verification

Run `python -m unittest discover -s tests -v` and `python sla_tracker.py` from
this directory. Tests cover business-hour boundaries, holiday exclusion, hold
pauses, due-by calculations, breach summaries, and malformed timestamp input.