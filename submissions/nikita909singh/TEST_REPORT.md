# Test Report: PS6 IT Service-Desk SLA Tracker

**Date:** 2026-10-27 · **Environment:** Windows 11, JDK 25 (compiled for Java 21), Maven 3.10

**Summary:** M1–M5 all work. 84/84 automated tests pass. All 10 sample tickets match hand-calculated
answers, and every invalid input tested is rejected with a specific message.

| Level | Result |
|---|---|
| Automated tests (`mvn clean package`) | ✅ 84 passed, 0 failed |
| Sample tickets vs hand calculation | ✅ 10/10 match |
| CLI checks on the packaged jar | ✅ All as expected |

## 1. Automated tests: 84 passed, 0 failed

| Suite | Tests | Result |
|---|---|---|
| BusinessCalendarTest | 24 | ✅ |
| SlaEngineTest | 22 | ✅ |
| InputLoaderTest | 30 | ✅ |
| MainTest (CLI) | 8 | ✅ |

## 2. Sample tickets vs hand calculation (as of Fri 2026-10-16 18:00 IST)

Holidays: Fri 2 Oct and Tue 20 Oct. Business hours Mon–Fri 09:00–18:00.

| Ticket | Rule it shows | Elapsed | Due by | Breach | State | Match |
|---|---|---|---|---|---|---|
| T-1001 | Simple same-day fix | 180 | 05 Oct 14:00 | 0 | MET | ✅ |
| T-1002 | Thursday 16:00 → over holiday + weekend → Monday 12:00 | 300 | 05 Oct 11:00 | 60 | BREACHED | ✅ |
| T-1003 | ON_HOLD for 1.5 days not counted (M3) | 240 | 09 Oct 12:00 | 0 | MET | ✅ |
| T-1004 | Still open, long overdue | 2940 | 14 Oct 11:00 | 1500 | BREACHED | ✅ |
| T-1005 | On hold at as-of: due-by unknown | 720 | (paused) | 0 | PAUSED | ✅ |
| T-1006 | 60 of 480 min left | 420 | 19 Oct 10:00 | 0 | AT_RISK | ✅ |
| T-1007 | RESOLVED then CLOSED | 900 | 16 Oct 16:00 | 0 | MET | ✅ |
| T-1008 | Raised Saturday: clock starts Monday 09:00 | 210 | 12 Oct 13:00 | 0 | MET | ✅ |
| T-1009 | Resolved then reopened: time adds up | 330 | 19 Oct 11:30 | 0 | ON_TRACK | ✅ |
| T-1010 | Due-by skips the 20 Oct holiday; ends exactly at 18:00 | 540 | 28 Oct 18:00 | 0 | ON_TRACK | ✅ |

**M5 summary:** P1 33.33%, P2 0%, P3 50%, P4 0%. Network 25%, Applications 50%, Service Desk 0%,
Unassigned 0%. Overall 20.00% (2 of 10).

## 3. Requirement checks

| Req | Check | Result |
|---|---|---|
| **M1** | Targets 240/480/1440/4320 min; only Mon–Fri 09:00–18:00 counted | ✅ |
| | Before 09:00, after 18:00, overnight and weekends add 0 | ✅ |
| | Custom work week (Mon–Sat 10:00–14:00) honoured | ✅ |
| | Daylight-saving weekend (New York, March 2026) counted correctly | ✅ |
| **M2** | Holiday adds 0 minutes; due-by skips holidays | ✅ |
| | Without the holidays file, T-1002 jumps from 300 to 840 minutes | ✅ |
| **M3** | ON_HOLD pauses; several holds; hold over a weekend; hold at creation | ✅ |
| | Breach before a hold stays a breach | ✅ |
| **M4** | Elapsed, due-by, breached, breach minutes in text, JSON and CSV | ✅ |
| | Exactly on target → not breached; 1 second late → breached, 1 minute | ✅ |
| **M5** | Breach % per priority, per group and overall, with open counts | ✅ |

## 4. Invalid input (one file with 10 tickets, 9 of them broken)

All 9 were reported together with their positions. Exit code 1, no report printed.

| Input | Message | Result |
|---|---|---|
| priority `P9` | `priority 'P9' has no SLA target (known: P1, P2, P3, P4)` | ✅ |
| createdAt `5th Oct` | `createdAt '5th Oct' is not an ISO-8601 time like ...` | ✅ |
| status `PARKED` | `statusHistory[0].status 'PARKED' is not a known status` | ✅ |
| status change before creation | `statusHistory[0].at is before createdAt` | ✅ |
| created after `--as-of` | `ticket B-5 was created after the as-of time ...` | ✅ |
| duplicate id | `id 'OK-1' is used by another ticket` | ✅ |
| missing id | `id is required ...` | ✅ |
| unknown field `severity` | `unknown field 'severity' (allowed: ...)` | ✅ |
| group `=HYPERLINK("x")` (CSV injection attempt) | `assigneeGroup must be 1-60 letters, ...` | ✅ |

| Other case | Result |
|---|---|
| Holiday `2026-13-01` | ✅ `not a valid date (YYYY-MM-DD)` |
| 14 kinds of broken policy (bad zone, start ≥ end, negative target, …) | ✅ All rejected (tests) |
| `--as-of next tuesday`, missing file, `--json` with `--csv`, unknown option | ✅ Exit 1 or 2 with a message |

## 5. Performance

| Scenario | Result |
|---|---|
| 20,000 tickets, each with 3 status changes (4.8 MB) | ✅ 3.6 s in total, vs 2.3 s for the 10-ticket sample (JVM startup); about 1.3 s of real work |
| 1,000 tickets open for 3 years each | ✅ Within the 5 s test limit |

## How to reproduce

```bash
mvn clean package
java -jar target/sla-tracker.jar report --tickets data/tickets.json \
     --policy data/sla_policy.json --holidays data/holidays.json --as-of 2026-10-16T18:00
```

## Verdict

M1–M5 are met, and all 10 sample tickets match hand-worked answers. Two bugs were found by these
checks during development and fixed (see PROMPTS.md). No known defects outstanding.
