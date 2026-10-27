# Test Report: PS1 Expense Splitter

**Date:** 2026-10-27 · **Environment:** Windows 11, JDK 25 (compiled for Java 21), Maven 3.10

**Summary:** M1–M5 all work. 72/72 automated tests pass. The settlement algorithm matches a brute-force
minimum on 1,500 random groups, and every invalid input is rejected with a clear message.

| Level | Result |
|---|---|
| Automated tests (`mvn clean package`) | ✅ 72 passed, 0 failed |
| CLI checks on the packaged jar | ✅ All as expected |
| Optimality vs brute force (1,500 random groups) | ✅ Always equal to the true minimum |

## 1. Automated tests: 72 passed, 0 failed

| Suite | Tests | Result |
|---|---|---|
| GroupTest: EqualSplit | 7 | ✅ |
| GroupTest: ExactSplit | 5 | ✅ |
| GroupTest: PercentageSplit | 6 | ✅ |
| GroupTest: CommonValidation | 9 | ✅ |
| GroupTest: Members + balances | 5 | ✅ |
| DebtSimplifierTest | 13 | ✅ |
| ExpenseFileTest | 18 | ✅ |
| MainTest (CLI) | 9 | ✅ |

## 2. Requirement checks on the real jar

| Req | Check | Result |
|---|---|---|
| **M1** | Equal split among everyone: ₹15,000 / 5 = 3,000 each | ✅ |
| | Equal split among a subset, odd paise: ₹4,250.50 / 4 = 1,062.63 ×2 + 1,062.62 ×2 | ✅ |
| | Exact split: ₹2,400 → 400 / 400 / 800 / 800 | ✅ |
| | Percentage split: ₹10,000 at 30/30/40 → 3,000 / 3,000 / 4,000 | ✅ |
| | ₹100 / 3 → 33.34 / 33.33 / 33.33 (adds up to exactly ₹100) | ✅ |
| **M2** | Paid, share and net per member; nets sum to 0 (also checked in `--json`) | ✅ |
| **M3** | Sample settles in 4 transfers, marked "proven minimum" | ✅ |
| | `greedy-vs-optimal.json`: 3 transfers (greedy would need 4) | ✅ |
| **M4** | Batch file (array of 5 expenses) | ✅ |
| | Single expense object; `add` command for each split type | ✅ |
| | `--json` output is valid JSON | ✅ |
| **M5** | Percentages adding up to 90 → `percentages add up to 90, not 100` | ✅ |
| | Exact shares short → `exact shares add up to 50.00 but the amount is 100.00` | ✅ |
| | Payer outside group → `payer 'Zed' is not a member of the group` | ✅ |

## 3. Edge cases (one file with 10 invalid expenses + 1 valid)

All 10 were reported together with their positions. Exit code 1, no report printed.
`--skip-invalid` settled using only the valid one.

| # | Input | Message | Result |
|---|---|---|---|
| 1 | percentages 50 + 40 | `percentages add up to 90, not 100` | ✅ |
| 2 | exact 30 + 20 of 100 | `exact shares add up to 50.00 but the amount is 100.00` | ✅ |
| 3 | payer "Zed" | `payer 'Zed' is not a member of the group` | ✅ |
| 4 | amount 0 | `amount must be greater than 0` | ✅ |
| 5 | amount −50 | `amount must be greater than 0` | ✅ |
| 6 | amount 10.005 | `amount must have at most 2 decimal places` | ✅ |
| 7 | amount `true` | `amount must be a number` | ✅ |
| 8 | split "thirds" | `split must be one of: equal, exact, percentage` | ✅ |
| 9 | participants Asha, ASHA | `'Asha' is listed more than once` | ✅ |
| 10 | field `paidby` (typo) | `unknown field 'paidby' (allowed: ...)` | ✅ |

| Other case | Result |
|---|---|
| Duplicate member names ("A", "a") | ✅ Rejected |
| Duplicate JSON keys | ✅ Rejected |
| Missing file | ✅ Clear error, exit 1 |
| `add` with invalid percentages | ✅ Rejected; file unchanged |
| `add` with lowercase payer `esha` | ✅ Recorded as `Esha` |
| Bad command lines (unknown option, missing value, `--amount ten`) | ✅ Exit 2 with usage |
| Hindi member name `आशा` | ✅ Accepted (this was a bug, fixed during testing) |

## 4. Performance

| Scenario | Result |
|---|---|
| 20 non-zero balances (exact DP at its limit) | ✅ Proven minimum, well within the 5 s test limit |
| 5,000 members (greedy fallback) | ✅ At most n−1 transfers, within the 5 s test limit |
| 5,000 expenses × 20 members through the CLI | ✅ 19 transfers, proven minimum, same run time as a 5-expense file (≈2.5 s, almost all JVM startup) |

## How to reproduce

```bash
mvn clean package
java -jar target/expense-splitter.jar summary data/expenses.json
java -jar target/expense-splitter.jar summary data/greedy-vs-optimal.json
java -jar target/expense-splitter.jar validate data/expenses.json
```

## Verdict

M1–M5 are met. Settlements are proven minimal for realistic group sizes, and every invalid-input case
tested is rejected with a specific message. No known defects outstanding.
