# PROMPTS.md — how this was built

Prompts I gave the assistant, and how I refined the result.

## 1. Initial ask

> Build a Python Expense Splitter (Splitwise-lite): three split types (equal /
> exact / percentage), net balances per member, debt simplification into
> "A pays B ₹X" settlements, JSON input (single or batch), and validation
> (percentages sum to 100, exact sums equal total, payer is a member).

## 2. Follow-up refinements

- **"Use integer paise for all money, not floats"** — avoids floating-point
  drift in equal splits and percentage rounding; every split still sums exactly
  to the total. (Led to the `to_paise` / `format_money` helpers and
  `Decimal` used only for parsing.)
- **"Make it runnable with no dependencies"** — standard library only, so it
  runs anywhere with Python 3.9+.
- **"What edge cases did you handle?"** — see the list below; I asked the
  assistant to enumerate and test each rather than just the happy path.

## Edge cases considered

| Case | Handling |
| --- | --- |
| Percentage decimals (33.33 / 66.67) | Parsed as hundredths-of-a-percent; last member absorbs rounding; sum validated to exactly 100.00 |
| Equal split with leftover paise (1000 ÷ 3) | Remainder distributed one paise at a time to first members; total always exact |
| Duplicate member names | Rejected at group creation and in equal-split lists |
| Payer not in group | Rejected |
| Zero / negative / NaN / Infinity amounts | Rejected |
| Single expense object vs. list | Both accepted (M4) |
| Exact amounts that don't match total | Rejected with the expected vs. actual totals in the message |
| No settlements needed (already square) | Empty list, friendly output |
| Missing/empty members | Rejected |

## 3. What I'd iterate on next (stretch)

- Cycle detection / linear-programming for the true minimum settlement count.
- A transaction log replay to reconcile balances against settlements.
- A small TUI or web UI over the same `Splitter` core.
