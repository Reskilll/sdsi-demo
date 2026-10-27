# PS1: Expense Splitter with Debt Simplification

A Splitwise-lite command-line tool for team outings. It records expenses with equal, exact or percentage
splits, shows everyone's net balance, and settles the group with the **proven minimum** number of
"A pays B ₹X" transfers.

📋 **[Test report](TEST_REPORT.md):** 72/72 automated tests, including a brute-force check that every
settlement plan is truly minimal.

- Java 21+ · Maven · Jackson (JSON) · JUnit 5
- Money is stored in integer paise, so there are no floating-point rounding errors and every split adds up
  to the exact total.

## Requirements coverage

| # | Requirement | How |
|---|---|---|
| M1 | Equal, exact and percentage splits | [`SplitCalculator`](src/main/java/com/sdsi/splitter/core/SplitCalculator.java) |
| M2 | Each member's net balance | `Group.balances()`: paid, share and net per member |
| M3 | Minimum list of settlements | [`DebtSimplifier`](src/main/java/com/sdsi/splitter/core/DebtSimplifier.java): exact optimum for up to 20 people with non-zero balances, greedy above that |
| M4 | Process `expenses.json`, single or batch | [`ExpenseFile`](src/main/java/com/sdsi/splitter/io/ExpenseFile.java): `"expenses"` can be an array or one object; the `add` command appends a single expense |
| M5 | Validation | Percentages sum to 100, exact shares sum to the total, the payer and participants are members, plus [many more checks](#validation) |

Extras: a proven-optimal settlement algorithm, `--json` output, `add` with atomic file writes,
case-insensitive names, Indian digit grouping (₹12,34,567.89), and every error reported at once.

## Quick start

```bash
cd submissions/singhkaram
mvn test                    # 72 tests
mvn package -DskipTests     # builds target/expense-splitter.jar
java -jar target/expense-splitter.jar summary data/expenses.json
```

> **Windows notes.** If Maven fails with `PKIX path building failed` (a proxy or antivirus intercepting
> TLS), set `MAVEN_OPTS="-Djavax.net.ssl.trustStoreType=Windows-ROOT"`. If `₹` shows up garbled in an old
> console, add `--ascii` to print `Rs.` instead.

### Sample output

```
Goa Team Outing: 5 members, 5 expense(s), total ₹31,750.50

EXPENSES
  e1    Villa (2 nights)     ₹15,000.00 paid by Asha         equal      Asha 3,000.00, Bhavesh 3,000.00, ...
  e2    Seafood dinner        ₹4,250.50 paid by Bhavesh      equal      Asha 1,062.63, Bhavesh 1,062.63, Chirag 1,062.62, Divya 1,062.62
  e3    Airport cabs          ₹2,400.00 paid by Chirag       exact      Asha 400.00, Bhavesh 400.00, Chirag 800.00, Esha 800.00
  e4    Scuba diving         ₹10,000.00 paid by Divya        percentage Asha 3,000.00, Divya 3,000.00, Esha 4,000.00
  e5    Snacks & water          ₹100.00 paid by Esha         equal      Asha 33.34, Bhavesh 33.33, Chirag 33.33

BALANCES
  Member             Paid           Share              Net
  Asha          15,000.00        7,495.97        +7,504.03  gets back
  Bhavesh        4,250.50        4,495.96          -245.46  owes
  Chirag         2,400.00        4,895.95        -2,495.95  owes
  Divya         10,000.00        7,062.62        +2,937.38  gets back
  Esha             100.00        7,800.00        -7,700.00  owes

SETTLEMENTS: 4 transfer(s), proven minimum
  Bhavesh pays Divya ₹245.46
  Chirag pays Divya ₹2,495.95
  Esha pays Asha ₹7,504.03
  Esha pays Divya ₹195.97
```

## Commands

| Command | What it does | Exit code |
|---|---|---|
| `summary FILE` | Prints expenses, balances and settlements. Any invalid expense stops the run and is listed. | 0 / 1 |
| `summary FILE --skip-invalid` | Reports invalid expenses, then settles using only the valid ones | 0 |
| `summary FILE --json` | Machine-readable output (amounts in rupees as decimals) | 0 / 1 |
| `validate FILE` | Lists every problem without printing a report | 0 / 1 |
| `add FILE --paid-by NAME --amount N --split equal\|exact\|percentage [--among A,B] [--shares A=300,B=200] [--desc TEXT] [--id ID]` | Validates one expense and appends it to the file | 0 / 1 |

Exit codes: `0` OK, `1` invalid data, `2` bad command line.

```bash
java -jar target/expense-splitter.jar add data/expenses.json --paid-by Esha --amount 600 \
     --split exact --shares "Asha=200,Bhavesh=400" --desc Parking
```

## Input format

```json
{
  "group": "Goa Team Outing",
  "members": ["Asha", "Bhavesh", "Chirag"],
  "expenses": [
    { "description": "Villa", "paidBy": "Asha", "amount": 9000, "split": "equal" },
    { "description": "Dinner", "paidBy": "Bhavesh", "amount": 1500, "split": "equal",
      "participants": ["Asha", "Bhavesh"] },
    { "description": "Cab", "paidBy": "Chirag", "amount": 900, "split": "exact",
      "shares": { "Asha": 300, "Chirag": 600 } },
    { "description": "Scuba", "paidBy": "Asha", "amount": 5000, "split": "percentage",
      "shares": { "Asha": 50, "Bhavesh": 25, "Chirag": 25 } }
  ]
}
```

- `expenses` can be an array (batch) or a single expense object. It can also be left out.
- `equal` splits among `participants`, or among all members if that is left out.
- `exact` shares are in rupees. `percentage` shares are percents (up to 4 decimals, e.g. `33.3333`).
- Amounts can be JSON numbers or numeric strings (`"250.50"`).
- To record a repayment ("Bhavesh paid Asha back ₹500"), add an `exact` expense paid by Bhavesh with
  `shares: {"Asha": 500}`.

See [`data/expenses.json`](data/expenses.json) and [`data/greedy-vs-optimal.json`](data/greedy-vs-optimal.json).

## Validation

Every problem in an expense is reported together, along with the expense's position in the file, so a
broken file can be fixed in one pass. An invalid expense never changes the group.

| Check | Example error |
|---|---|
| Percentages sum to exactly 100 | `percentages add up to 99.99, not 100` |
| Exact shares sum to the amount | `exact shares add up to 800.00 but the amount is 900.00` |
| Payer is a group member | `payer 'Zed' is not a member of the group` |
| Participants are members, not repeated | `'Asha' is listed more than once` |
| Amount > 0, at most 2 decimals, at most ₹1 crore | `amount must have at most 2 decimal places` |
| Shares not negative; percentages 0–100 | `share for 'Bhavesh' must not be negative` |
| Split type is equal, exact or percentage | `split must be one of: equal, exact, percentage` |
| `participants` only for equal, `shares` only for exact/percentage | `an equal split takes 'participants', not 'shares'` |
| No unknown fields (catches typos like `paidby`) | `unknown field 'paidby' (allowed: ...)` |
| No duplicate JSON keys, no booleans or text where numbers belong | `amount must be a number` |
| Member names unique ignoring case; 1–40 letters (any script), digits, spaces, `. _ ' -` | `member 'asha' is listed more than once` |
| Expense ids unique | `id 'e1' is already used by another expense` |
| Limits: 20 MB file, 500 members, 100,000 expenses, 30-digit numbers | |

Names match case-insensitively: `"paidBy": "asha"` is recorded as `Asha`.

## Design

```
cli/Main ─► io/ExpenseFile ─► core/Group ─► core/SplitCalculator   (M1, M5)
                                   │
                                   ├─► balances()                  (M2)
                                   └─► core/DebtSimplifier         (M3)
            io/ReportWriter (text / JSON)
```

### Rounding

Money is kept as `long` paise. Each split rounds down, then the leftover paise go one each to the
people with the largest rounded-off fraction (the *largest remainder method*). Ties go to whoever is listed
first. So ₹100 split three ways is 33.34 / 33.33 / 33.33: always the exact total, and the same result
every time.

### Debt simplification (M3)

The simple approach is greedy: the biggest debtor pays the biggest creditor, repeated. That never takes
more than n−1 transfers, but **it isn't minimal**. Take balances `+100, +90, −90, −60, −40`. Greedy needs
4 transfers, but 3 are enough because `{+90, −90}` and `{+100, −60, −40}` can settle separately.

The minimum is *(people with a non-zero balance) − (the most groups they can be split into where each
group's balances sum to zero)*. Finding that split is NP-hard, so:

- **Up to 20 people with non-zero balances** (any realistic outing): dynamic programming over subsets,
  O(2ⁿ·n), finds the best split. Each group is then settled greedily. The result is **proven minimal**,
  and the output says so.
- **More than 20:** greedy with heaps, O(n log n), at most n−1 transfers. The output marks it
  "near-minimum".

Tests check the exact algorithm against a brute-force search on 1,500 random groups, and check that
every plan brings every balance to exactly zero.

### Performance

| Operation | Cost |
|---|---|
| Add an expense | O(participants) |
| Balances | O(total shares) |
| Settlement (n ≤ 20 non-zero balances) | O(2ⁿ·n), under 1 s at n = 20 |
| Settlement (n > 20) | O(n log n); 5,000 people settle well within the 5 s test limit |

A 5,000-expense file runs in about the same time as a 5-expense one: almost all of it is JVM startup.

## Security and robustness

- The input file is treated as untrusted. Its size, nesting depth, string length and number length are
  capped, duplicate keys are rejected, and unknown fields are rejected.
- Names use an allow-list pattern, so there is no control-character or terminal-escape injection into
  the report.
- `add` validates the whole file plus the new expense before writing. It writes to a temporary file
  and then moves it into place, so a crash never leaves a corrupt file.
- Amounts are capped at ₹1 crore per expense, which keeps all sums far from `long` overflow.

## Tests (72)

| Suite | Covers |
|---|---|
| `GroupTest` | All three split types, rounding, every validation rule, case-insensitive names, Unicode names, failed adds leaving no trace, balances |
| `DebtSimplifierTest` | Empty, chain and zero-sum-group cases; **matches the brute-force minimum on 1,500 random groups**; 20-person exact case under 5 s; 5,000-person greedy fallback; determinism |
| `ExpenseFileTest` | Sample file, single vs batch, numeric strings, broken files, per-expense error positions, atomic append |
| `MainTest` | Every command and flag, exit codes, `--json` validity, `--skip-invalid`, `add` for each split type |
