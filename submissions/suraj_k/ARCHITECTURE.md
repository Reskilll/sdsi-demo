# Splitwise-Lite: Team Outing Expense Settler — Architecture Blueprint

## 1. Design Philosophy

- **Single Responsibility**: Every class does exactly one thing. Expense knows its data; Split computes shares; SettlementService finds the optimal transfer plan.
- **Open/Closed**: New split types (e.g., "by-item") are added by subclassing `Split`, not by modifying existing code.
- **Validation at the boundary**: Input is rejected as early as possible with precise, actionable error messages.
- **Immutable where practical**: `Expense` and `Split` objects are value objects — constructed once, never mutated.
- **Algorithm transparency**: The debt-simplification algorithm is a pure function with no side effects, trivially testable.

---

## 2. Domain Model (Core Entities)

```
Member
  ├── id: str (uuid)
  ├── name: str
  └── __eq__, __hash__  (identity by id)

Split            (abstract)
  ├── participants: list[Member]
  ├── total_amount: Decimal
  ├── validate() -> None           # raises on violation
  ├── share_for(member) -> Decimal # what one member owes
  └── shares() -> dict[Member, Decimal]
      │
      ├── EqualSplit      total / N per participant
      ├── ExactSplit      per-member explicit amounts; sum == total
      └── PercentageSplit per-member %; sum == 100

Expense
  ├── id: str (uuid)
  ├── description: str
  ├── payer: Member
  ├── total_amount: Decimal
  ├── split: Split
  ├── created_at: datetime
  └── validate() -> None   # payer is in participants, amount > 0

Transaction                   (output of debt simplification)
  ├── from_member: Member
  ├── to_member: Member
  └── amount: Decimal

BalanceSnapshot               (per-member net position)
  ├── member: Member
  ├── paid: Decimal           # total this member paid
  ├── owed: Decimal           # total this member owes from their own share
  └── net: Decimal            # paid - owed  (+: creditor, -: debtor)
```

---

## 3. Service Layer

```
GroupManager                   (aggregate root for a group)
  ├── members: set[Member]
  ├── expenses: list[Expense]
  ├── add_member(name) -> Member
  ├── add_expense(description, payer_id, amount, split_data) -> Expense
  │     validates payer exists, creates split, validates split, stores
  ├── net_balances() -> list[BalanceSnapshot]
  └── simplify_debts() -> list[Transaction]

BalanceCalculator              (pure functions, no state)
  ├── compute(members, expenses) -> list[BalanceSnapshot]
  └── format(balances) -> str

SettlementEngine               (pure function, no state)
  └── simplify(balances: list[BalanceSnapshot]) -> list[Transaction]
        Algorithm: greedy max-flow with dual max-heaps
        O(n log n) where n = number of members
```

---

## 4. Algorithm: Debt Simplification (M3)

```
PROCEDURE simplify(balances):
    creditors ← MaxHeap()   # members with net > 0, keyed by net
    debtors   ← MaxHeap()   # members with net < 0, keyed by |net|
    
    FOR each balance b:
        IF b.net > ε:  creditors.push(b.member, b.net)
        IF b.net < -ε: debtors.push(b.member, -b.net)
    
    transactions ← []
    
    WHILE creditors NOT empty AND debtors NOT empty:
        (creditor, credit_amt) ← creditors.pop()
        (debtor,   debit_amt)  ← debtors.pop()
        
        settle_amt ← min(credit_amt, debit_amt)
        transactions.append(Transaction(debtor, creditor, settle_amt))
        
        IF credit_amt > settle_amt:
            creditors.push(creditor, credit_amt - settle_amt)
        IF debit_amt > settle_amt:
            debtors.push(debtor, debit_amt - settle_amt)
    
    RETURN transactions
```

**Correctness**: This greedy algorithm is optimal for minimizing the number of transactions — it's equivalent to the "splitwise problem" solved by subset-sum heuristics, and the max-heap greedy is the standard practical approximation that produces the minimum number of transactions in the non-cyclic case.

**Edge case**: When net balances don't sum to zero (floating-point drift), the final remainder < ε is silently absorbed.

---

## 5. JSON Processing (M4) — Input Schema

```json
{
  "group": {
    "name": "Team Outing 2026",
    "members": ["Alice", "Bob", "Charlie", "Diana"]
  },
  "expenses": [
    {
      "description": "Dinner at Luigi's",
      "payer": "Alice",
      "amount": 120.00,
      "split": {
        "type": "equal",
        "participants": ["Alice", "Bob", "Charlie", "Diana"]
      }
    },
    {
      "description": "Taxi",
      "payer": "Bob",
      "amount": 45.00,
      "split": {
        "type": "exact",
        "participants": ["Alice", "Bob", "Charlie"],
        "amounts": { "Alice": 15.00, "Bob": 15.00, "Charlie": 15.00 }
      }
    },
    {
      "description": "Hotel Suite",
      "payer": "Diana",
      "amount": 400.00,
      "split": {
        "type": "percentage",
        "participants": ["Alice", "Diana"],
        "percentages": { "Alice": 40, "Diana": 60 }
      }
    }
  ]
}
```

### Output Schema

```json
{
  "group": "Team Outing 2026",
  "member_count": 4,
  "expense_count": 3,
  "total_spent": 565.00,
  "net_balances": [
    { "member": "Alice",   "paid": 120.00, "owed": 220.00, "net": -100.00 },
    { "member": "Bob",     "paid": 45.00,  "owed": 45.00,  "net": 0.00 },
    { "member": "Charlie", "paid": 0.00,   "owed": 45.00,  "net": -45.00 },
    { "member": "Diana",   "paid": 400.00, "owed": 255.00, "net": 145.00 }
  ],
  "settlements": [
    { "from": "Alice", "to": "Diana", "amount": 100.00 },
    { "from": "Charlie", "to": "Diana", "amount": 45.00 }
  ]
}
```

---

## 6. Validation Rules (M5)

| Rule | Enforcement Point | Error Message |
|------|------------------|---------------|
| Payer is a valid member | `GroupManager.add_expense` | `"Payer 'X' is not a member of the group"` |
| All participants are valid members | `Split.__init__` | `"Participant 'X' is not a member of the group"` |
| Amount > 0 | `Expense.__init__` | `"Expense amount must be positive, got X"` |
| At least 2 participants | `Split.__init__` | `"At least 2 participants required"` |
| ExactSplit: sum(amounts) == total | `ExactSplit.validate` | `"Exact amounts sum to X, expected total Y"` |
| PercentageSplit: sum(%) == 100 | `PercentageSplit.validate` | `"Percentages sum to X%, expected 100%"` |
| Non-empty member list in group | `JSONProcessor` | `"Group must have at least 2 members"` |
| No duplicate member names | `GroupManager.add_member` | `"Member 'X' already exists"` |
| Expense list can be empty | N/A | Valid — just report zero balances |

---

## 7. Error Handling Strategy

- **Custom exception hierarchy**: `SplitwiseError` → `ValidationError`, `MemberNotFoundError`, `SplitValidationError`
- **JSON layer**: `InputValidationError` with field-level `path` and `detail` for precise error localization
- **Batch mode**: Collect ALL errors before failing — no fail-on-first. Process entire JSON, report every violation.
- **Decimal everywhere**: All monetary values use `Decimal` with `ROUND_HALF_UP`, precision 0.01. Never `float`.
- **Idempotency**: `add_expense` returns the expense; calling it twice with the same data creates two expenses (this is correct — each dinner is its own expense). The API does not try to deduplicate.

---

## 8. File Layout

```
submissions/suraj_k/
├── ARCHITECTURE.md          # This document
├── README.md                # Usage guide
├── requirements.txt         # (empty — stdlib only)
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── member.py        # Member value object
│   │   ├── split.py         # Split ABC + Equal/Exact/Percentage
│   │   ├── expense.py       # Expense value object
│   │   ├── transaction.py   # Transaction + BalanceSnapshot
│   ├── services/
│   │   ├── __init__.py
│   │   ├── group_manager.py # Aggregate root
│   │   ├── balance.py       # BalanceCalculator
│   │   ├── settlement.py    # SettlementEngine (algorithm)
│   │   ├── json_processor.py# JSON batch/single processing
│   ├── errors.py            # Exception hierarchy
│   ├── cli.py               # Command-line entry point
├── tests/
│   ├── __init__.py
│   ├── test_split.py
│   ├── test_expense.py
│   ├── test_balance.py
│   ├── test_settlement.py
│   ├── test_group_manager.py
│   ├── test_json_processor.py
│   ├── test_validation.py
│   ├── test_integration.py
│   ├── fixtures/
│   │   ├── sample_equal.json
│   │   ├── sample_exact.json
│   │   ├── sample_percentage.json
│   │   ├── sample_mixed.json
│   │   ├── invalid_percentage.json
│   │   ├── invalid_exact.json
│   │   └── invalid_payer.json
├── run.py                    # Convenience launcher
```

---

## 9. CLI Interface

```bash
# Single JSON file
python run.py input.json

# Batch directory
python run.py batch/input_directory/

# Stdout pipe
cat input.json | python run.py --stdin

# Pretty-print balances only
python run.py input.json --balances-only

# Output to file
python run.py input.json --output result.json
```

---

## 10. Quality Guarantees

- **100% Decimal arithmetic**: No floating-point for money. Fractions resolve to 2 decimal places with banker's rounding.
- **Comprehensive tests**: Every split type, every validation rule, edge cases (0-member group, single-member, large groups), and the debt simplification algorithm on known-optimal cases.
- **Type hints throughout**: `mypy --strict` clean.
- **No external dependencies**: stdlib only (`decimal`, `json`, `heapq`, `uuid`, `argparse`, `pathlib`, `unittest`).
- **Security guards**: File size cap (50MiB), member name character validation, input size limits, sub-paisa precision rejection.

## 11. Implementation Evolution (Post-Blueprint)

The following were added during implementation beyond the original blueprint:

| Enhancement | Edge Case | Mechanism |
|------------|-----------|-----------|
| Soft-delete (`Member.active`) | Inactive members | Tombstone preserves referential integrity |
| `MONEY_CONTEXT` (prec=28) | Large-scale precision | Explicit Decimal context |
| `validate_amount()` with NaN/Inf guard | Malicious JSON | `Decimal(str()).is_finite()` check |
| Duplicate-participant rejection | Split corruption | `set()` check in `Split.__init__` |
| Negative exact amount rejection | Unlisted | Guard in `ExactSplit.__init__` |
| Negative percentage rejection | Unlisted | Guard in `PercentageSplit.__init__` |
| Member name control-char filter | Security | Regex in `JSONProcessor._build_group()` |
| File size limit (50 MiB) | DoS prevention | `Path.stat().st_size` before parse |
| Description length cap (500) | Log flooding | Guard in `_add_expense_from_dict()` |
| Member count cap (10,000) | Heap exhaustion | Guard in `_build_group()` |
| Expense count cap (100,000) | OOM in balance | Guard in `_build_group()` |
| `PROMPTS.md` | AI collaboration | Full prompt traceability matrix |
| `.gitignore` | Git hygiene | Python-standard patterns |