# Expense Settler — C++ (Splitwise-lite)

A zero-dependency C++ tool for settling team-outing expenses. Add expenses
with three split types, see net balances, and get the minimum list of
"who pays whom" settlements.

## Quick start

```bash
mkdir build && cd build
cmake ..
cmake --build .
./expense-settler ../sample_expenses.json
```

Requires **CMake ≥ 3.16** and a **C++17** compiler (GCC 8+, Clang 7+, MSVC 2019+).

## Features

| Feature | Description |
|---------|-------------|
| **M1 — Three split types** | Equal, exact amounts, percentage |
| **M2 — Net balances** | Per-member net balance (positive = owed) |
| **M3 — Debt simplification** | Greedy min-transactions algorithm |
| **M4 — JSON input** | Single object or batch array |
| **M5 — Input validation** | Percentages sum to 100%, exact amounts match total, payer in group |

## Usage

```
expense-settler <expenses.json>           # process and print report
expense-settler --validate <file.json>    # validate only
```

## JSON input format

```json
[
  {
    "description": "Dinner at Punjabi Dhaba",
    "paid_by": "Ajay",
    "amount": 2400,
    "split_type": "equal",
    "members": ["Ajay", "Priya", "Rohan", "Neha"]
  },
  {
    "description": "Museum tickets",
    "paid_by": "Rohan",
    "amount": 1000,
    "split_type": "exact",
    "members": ["Ajay", "Priya", "Rohan"],
    "shares": { "Ajay": 500, "Priya": 300, "Rohan": 200 }
  },
  {
    "description": "Snacks",
    "paid_by": "Neha",
    "amount": 800,
    "split_type": "percentage",
    "members": ["Ajay", "Priya", "Rohan", "Neha"],
    "shares": { "Ajay": 30, "Priya": 25, "Rohan": 25, "Neha": 20 }
  }
]
```

### Fields

| Field | Required | Notes |
|-------|----------|-------|
| `description` | Yes | Non-empty string |
| `paid_by` | Yes | Must be a member of the group |
| `amount` | Yes | Positive number (in ₹, can be float) |
| `split_type` | Yes | One of: `equal`, `exact`, `percentage` |
| `members` | Yes | Non-empty array of unique strings |
| `shares` | For exact & percentage | Map of member → amount or % |

## Running tests

```bash
cd build
cmake --build .
ctest              # or ./expense-settler-tests
```

## Design decisions

### Money as integer paise
All amounts are stored as `int64_t` paise (₹1 = 100 paise). No floating-point
money — eliminates rounding errors. Conversion to/from JSON doubles uses
`llround()`.

### Greedy debt simplification
The algorithm sorts creditors and debtors, then greedily pairs the largest of
each. This is optimal for the unrestricted variant (you can pay anyone).

### Zero external dependencies
A minimal JSON parser (~250 lines) is bundled — no nlohmann/json, no third-party
libs. Compiles with a single `cmake` invocation.

### Rounding
Equal splits distribute the remainder 1-paisa to the first N members.
Percentage splits give the remainder to the last member. Net balances always
sum to zero.

## Edge cases handled

- **Zero expenses** → empty report
- **Single-member expense** → net balance of 0
- **Duplicate members** → validation error
- **Negative/zero amounts** → validation error
- **Payer not in expense members** → validation error
- **Percentage ≠ 100%** → validation error
- **Exact sum ≠ total** → validation error
- **Large amounts** → handled via int64_t (up to ₹92 quadrillion)
- **All settled** → outputs "All settled up!"
- **Rounding drift** → remainder distributed deterministically
- **JSON file safety** → 10 MB size limit, UTF-8 encoding

## Project structure

```
expense_settler/
├── include/expense_settler/
│   ├── models.hpp       # Data structures
│   ├── validator.hpp    # Input validation
│   ├── engine.hpp       # Balance + settlement logic
│   ├── json_loader.hpp  # JSON file parser
│   └── cli.hpp          # Report generator
├── src/
│   ├── main.cpp         # Entry point
│   ├── validator.cpp
│   ├── engine.cpp
│   ├── json_loader.cpp
│   └── cli.cpp
├── tests/
│   ├── test.hpp         # Minimal test harness
│   └── test_engine.cpp  # 15+ test cases
├── sample_expenses.json  # 5-expense batch
├── sample_single.json    # 1-expense (single object)
├── CMakeLists.txt
├── README.md
└── PROMPTS.md
```

## License

MIT