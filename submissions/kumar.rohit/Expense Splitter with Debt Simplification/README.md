# Expense Splitter with Debt Simplification

A lightweight expense-sharing application that allows a group of members to
record shared expenses, calculate each member's net balance, and generate a
simplified settlement list.

## Features

- **Three split types**: equal, exact, and percentage.
- **Debt simplification**: greedy largest-debtor/largest-creditor algorithm
  that produces a minimal (near-minimum) set of settlement transactions.
- **Optional exact solver**: DP-based subset-sum solver for globally minimal
  transactions on groups with ≤12 non-zero balance members.
- **Web UI**: responsive single-page application with dashboard, expenses,
  members, settlements, and JSON import.
- **Atomic batch processing**: validates all input before any calculation;
  rejects the entire batch with all error messages if anything is invalid.
- **Input validation**: exhaustive validation of all JSON fields, types, ranges,
  duplicates, monetary precision, and invariants (exact sums, percentage totals).
- **JSON output**: machine-readable output for programmatic consumption.
- **Human-readable output**: pretty-printed terminal output with ₹ formatting.
- **Deterministic**: identical input always produces identical output.
- **No floating-point**: all monetary values use Python's `Decimal` with
  round-half-up to 2 decimal places (paise precision for INR).

## Requirements

- Python 3.11+
- No external dependencies for production code (stdlib only).
- `pytest` for running tests.

## Installation

```bash
git clone <repo>
cd "Expense Splitter with Debt Simplification"
pip install -r requirements.txt   # only installs pytest
```

## Usage

### CLI Mode

```bash
# Human-readable output
python -m expense_splitter --input expenses.json

# JSON output
python -m expense_splitter --input expenses.json --json

# Write to file
python -m expense_splitter --input expenses.json --output result.json

# Balances only
python -m expense_splitter --input expenses.json --balances-only

# Settlements only
python -m expense_splitter --input expenses.json --settlements-only

# Use exact minimum-transaction solver
python -m expense_splitter --input expenses.json --exact
```

### Web UI Mode

```bash
# Start the web server
python -m expense_splitter --serve

# Custom port
python -m expense_splitter --serve --port 9000

# Then open http://localhost:8080 in your browser
```

The web UI provides:
- **Dashboard**: overview with stat cards, recent expenses, and member balances.
- **Expenses**: full expense list with search, filter by payer/type, and delete.
- **Members**: member management with add/remove and balance status.
- **Settle Up**: settlement view with copy-all, copy-individual, and JSON export.
- **Import**: drag-and-drop JSON import with preview and validation.
- **Settings**: currency info and data reset.

### Backend Integration

The web UI communicates with the Python backend via a REST API at `/api/*`.
All financial calculations run on the backend using `Decimal` arithmetic.
The frontend never performs its own monetary calculations.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/group` | GET | Full group data (members, expenses, balances, settlements) |
| `/api/balances` | GET | Member balances only |
| `/api/settlements` | GET | Settlement suggestions only |
| `/api/members` | GET | Members list |
| `/api/expenses` | GET | Expenses list |
| `/api/expenses` | POST | Add a new expense |
| `/api/members` | POST | Add a new member |
| `/api/import` | POST | Import full batch (members + expenses) |
| `/api/reset` | POST | Reset to demo data |
| `/api/expenses/{id}` | DELETE | Delete an expense |
| `/api/members/{id}` | DELETE | Delete a member |

```bash
git clone <repo>
cd "Expense Splitter with Debt Simplification"
pip install -r requirements.txt   # only installs pytest
```

## Usage

```bash
# Human-readable output
python -m expense_splitter --input expenses.json

# JSON output
python -m expense_splitter --input expenses.json --json

# Write to file
python -m expense_splitter --input expenses.json --output result.json

# Balances only
python -m expense_splitter --input expenses.json --balances-only

# Settlements only
python -m expense_splitter --input expenses.json --settlements-only

# Use exact minimum-transaction solver (for groups ≤ 12 non-zero members)
python -m expense_splitter --input expenses.json --exact
```

## JSON Input Schema

```json
{
  "members": [
    {"id": "alice", "name": "Alice"},
    {"id": "bob", "name": "Bob"}
  ],
  "expenses": [
    {
      "expense_id": "exp1",
      "description": "Dinner at Taj",
      "amount": 1000.00,
      "currency": "INR",
      "payer": "alice",
      "participants": ["alice", "bob", "charlie"],
      "split_type": "equal"
    }
  ]
}
```

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `members` | array | yes | At least 1 member |
| `members[].id` | string | yes | Unique, non-empty |
| `members[].name` | string | no | Display name |
| `expenses` | array | yes | May be empty |
| `expenses[].expense_id` | string | yes | Unique, non-empty |
| `expenses[].description` | string | no | Defaults to "" |
| `expenses[].amount` | number | yes | Positive, ≤9,999,999,999.99, max 2 decimal places |
| `expenses[].currency` | string | no | Default "INR". Only "INR" currently supported |
| `expenses[].payer` | string | yes | Must be a known member ID |
| `expenses[].participants` | array | yes | Non-empty, no duplicates, all known members |
| `expenses[].split_type` | string | yes | One of: "equal", "exact", "percentage" |
| `expenses[].split_details` | array | required for exact/percentage | Split entries |
| `expenses[].timestamp` | string | no | ISO 8601 timestamp |

### Split Types

#### Equal Split (`split_type: "equal"`)
Each participant bears an equal share. `split_details` is optional and ignored.

#### Exact Split (`split_type: "exact"`)
Each `split_details` entry specifies `member_id` and exact `value` (amount).
Values must be positive, at most 2 decimal places, and sum to exactly `amount`.

```json
"split_details": [
  {"member_id": "alice", "value": 200.00},
  {"member_id": "bob", "value": 300.00},
  {"member_id": "charlie", "value": 500.00}
]
```

#### Percentage Split (`split_type: "percentage"`)
Each `split_details` entry specifies `member_id` and percentage `value` (0–100).
Percentages must sum to 100.00% (within 0.005% tolerance).

```json
"split_details": [
  {"member_id": "alice", "value": 20},
  {"member_id": "bob", "value": 30},
  {"member_id": "charlie", "value": 50}
]
```

## Balance Sign Convention

- **Positive net balance**: the member is owed money (should receive).
- **Negative net balance**: the member owes money.
- **Zero net balance**: the member is settled.

`net_balance = total_paid - total_share`

- `total_paid`: sum of all expense amounts where this member was the payer.
- `total_share`: sum of all shares allocated to this member across all expenses.

## Monetary Precision and Rounding

All monetary values use Python's `Decimal` type with **half-up** rounding to
**2 decimal places** (paise for INR).

### Equal Split Rounding Strategy
1. Each participant gets `floor(amount / n)` rounded to 2 decimal places.
2. Any remainder (in paise) is distributed one paise at a time to the first N
   participants in list order, ensuring the total equals the expense amount.

This is deterministic and guarantees exact sum preservation.

### Percentage Split Rounding Strategy
1. Each share = `round(amount * percentage / 100, 2)` using round-half-up.
2. Any rounding remainder (in paise) is distributed one paise at a time to
   participants in list order.

### Example: ₹100 among 3 people (equal split)
| Participant | Share |
|-------------|-------|
| First | ₹33.34 |
| Second | ₹33.33 |
| Third | ₹33.33 |
| **Total** | **₹100.00** |

## Debt Simplification Algorithm

### Greedy Strategy (Default) — O(n log n)

1. Separate members into **debtors** (negative balance) and **creditors**
   (positive balance). Zero-balance members are excluded.
2. Use max-heaps to efficiently find the largest debtor and largest creditor.
3. In each iteration:
   a. Pop the largest debtor (D) and largest creditor (C).
   b. Settle `min(debt(D), credit(C))` from D → C.
   c. Push back any remainder.
4. Tie-breaking: when amounts are equal, the entry with the lower insertion
   index wins (deterministic).

**Complexity**: O(n log n) time, O(n) space.

**Guarantees**:
- No self-transfers.
- No zero or negative settlement amounts.
- All parties are known group members.
- Applying all settlements brings every balance to zero.
- Deterministic output for identical input.

**Optimality**: This algorithm does **NOT** guarantee a globally minimum number
of transactions. It is a 2-approximation (uses at most 2×(optimum) transactions).

### Exact Strategy (Optional) — O(n × 2^n)

For small groups (≤12 non-zero balance members), an exact DP solver finds the
globally minimum number of transactions by partitioning the set into zero-sum
subsets and settling each subset greedily.

**Complexity**: O(n × 2^n) time, O(2^n) space.

Activate with `--exact` flag. For groups larger than the limit, the exact solver
is bypassed and greedy is used (configurable via `exact_limit` parameter).

## Validation and Error Handling

All JSON input is validated atomically before any calculation:
- All errors are collected into a single report.
- If any validation error is found, the entire batch is rejected.
- Error messages include the expense ID and field context.

### Validated Constraints

| Constraint | Error |
|------------|-------|
| Missing required fields | `missing required field` |
| Duplicate member IDs | `duplicate member ID` |
| Duplicate expense IDs | `duplicate expense ID` |
| Unknown payer | `unknown member` |
| Unknown participant | `unknown member` |
| Empty participant list | `must not be empty` |
| Negative/zero expense amount | `must be positive` |
| Boolean/NaN/Infinity amounts | `must be a number` |
| Excessive decimal precision | `too many decimal places` |
| Invalid split type | `unsupported split type` |
| Exact amounts not summing to total | `does not equal expense total` |
| Percentages not summing to 100% | `must sum to 100%` |
| Negative percentage | `must not be negative` |
| Percentage > 100 | `must not exceed 100` |
| Duplicate participants | `duplicate participant` |
| Unsupported currency | `unsupported currency` |
| Empty member list | `must contain at least one member` |
| Non-object JSON input | `must be a JSON object` |
| Missing members/expenses fields | `missing required field` |
| Members/expenses not arrays | `must be a list` |
| Amount exceeds max | `exceeds maximum allowed` |

## How to Run Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Known Limitations

1. **Single currency**: only INR is supported. Multi-currency expenses require
   exchange rate data and are out of scope.
2. **Greedy settlement not globally optimal**: the greedy algorithm produces a
   near-minimal set of transactions but not always the absolute minimum. Use
   `--exact` for small groups (≤12 non-zero members) to get global optimality.
3. **No persistence**: expenses are read from JSON files only. No database
   backing.
4. **Atomic validation only**: the entire batch is validated before any
   processing. There is no "partial" or "best-effort" mode. If partial
   processing is ever added, it should be an explicit opt-in with clear
   per-record error reporting.
5. **No undo/rollback**: settlements are computed in-memory only.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| `Decimal` for all money | Avoids floating-point errors that would compound across expenses |
| Round-half-up | Standard consumer finance convention (vs. banker's rounding) |
| Remainder to first N participants | Simple, deterministic, preserves total |
| Greedy largest-debtor/largest-creditor | O(n log n), easy to explain, produces good results |
| Max-heap with insertion-index tie-break | Deterministic output for identical input |
| Exact DP solver optional | O(2^n) is impractical for large groups; configurable limit |
| Atomic batch validation | Prevents misleading partial results |
| No dependencies beyond stdlib | Minimizes install friction |
| Frozen dataclasses throughout | Immutable models prevent accidental mutation bugs |

## Project Structure

```
expense_splitter/
├── __init__.py        # Package metadata
├── __main__.py        # CLI (--input, --serve, --json, etc.)
├── models.py          # Data models (Member, Expense, Balance, Settlement)
├── exceptions.py      # Custom exceptions and ValidationReport
├── splits.py          # Split calculation (equal, exact, percentage)
├── balances.py        # Balance aggregation
├── simplify.py        # Debt simplification (greedy + exact DP)
├── validation.py      # Input validation
├── engine.py          # Pipeline orchestration + invariant checks
├── io.py              # JSON I/O and output formatting
└── server.py          # HTTP API server for web UI
static/
├── index.html         # SPA shell
├── css/
│   └── style.css      # Design system and responsive styles
└── js/
    ├── api.js         # API client + formatting utilities
    ├── components.js  # Reusable UI components (cards, modals, avatars, icons)
    ├── pages.js       # Page definitions (dashboard, expenses, members, settle-up, import, settings)
    └── app.js         # Application shell, routing, and state
tests/
├── test_splits.py     # Split calculation tests
├── test_balances.py   # Balance calculation tests
├── test_simplify.py   # Debt simplification tests
├── test_validation.py # Input validation tests
└── test_integration.py # Integration, JSON I/O, CLI tests
expenses.json          # Sample input
requirements.txt       # pytest

## Example Output

```
============================================================
  EXPENSE SPLITTER - RESULTS
============================================================

Processed: 5 expense(s) across 5 member(s)

----------------------------------------
  BALANCES
----------------------------------------
  Member                     Paid      Share        Net
  -----------------------------------------------------
  alice                   1000.00     793.34    +206.66
  bob                      600.00     773.33    -173.33
  charlie                  800.00     883.33     -83.33
  diana                    750.50     250.00    +500.50
  eve                        0.00     450.50    -450.50

----------------------------------------
  SETTLEMENTS
----------------------------------------
  eve pays diana ₹450.50
  bob pays alice ₹173.33
  charlie pays diana ₹50.00
  charlie pays alice ₹33.33

============================================================
```