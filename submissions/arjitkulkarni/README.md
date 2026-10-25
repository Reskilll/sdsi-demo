# PS1 — Expense Splitter with Debt Simplification

A small, dependency-free Splitwise-lite CLI for settling a team outing.
Feed it a JSON file of expenses and it prints each member's net balance and
a short list of "A pays B ₹X" settlements.

## Run it

Requires **Node.js 18+**. There is nothing to install.

```bash
cd submissions/arjitkulkarni
npm start                      # sample batch, with USD converted via data/rates.json
npm test                       # 33 tests using the built-in node:test runner

node src/cli.js data/expenses.json --rates data/rates.json          # human-readable
node src/cli.js data/expenses.json --rates data/rates.json --json   # machine-readable
node src/cli.js data/invalid.json                                   # shows validation errors, exit code 1
```

Sample output:

```
Net balances (+ is owed, - owes):
  Asha   -₹1677.90
  Ravi   -₹477.05
  Meera  +₹1666.47
  Kabir  +₹488.48
  Zoya   ₹0.00

Settlements (3):
  Asha pays Meera ₹1666.47
  Asha pays Kabir ₹11.43
  Ravi pays Kabir ₹477.05
```

## Input format

```jsonc
{
  "members": ["Asha", "Ravi", "Meera"],
  "expenses": [                      // an array (batch) or a single expense object
    { "id": "e1", "paidBy": "Asha", "amount": 100,
      "split": { "type": "equal", "among": ["Asha", "Ravi", "Meera"] } },  // "among" defaults to everyone
    { "id": "e2", "paidBy": "Ravi", "amount": 500,
      "split": { "type": "exact", "shares": { "Asha": 300, "Ravi": 200 } } },
    { "id": "e3", "paidBy": "Meera", "amount": 30, "currency": "USD",       // optional; needs --rates
      "split": { "type": "percentage", "shares": { "Asha": 33.33, "Ravi": 33.33, "Meera": 33.34 } } }
  ]
}
```

`rates.json` holds fixed rates into a base currency: `{ "base": "INR", "rates": { "USD": 83.25 } }`.

## How each requirement is met

| Req | Where | How |
|---|---|---|
| M1 three split types | `src/splitter.js` | `equal`, `exact`, `percentage` (up to 2 decimals, e.g. 33.33%) |
| M2 net balances | `computeBalances` | net = paid − owed per member; asserted to sum to exactly 0 |
| M3 simplify debts | `src/settle.js` | exact-match pairing, then a greedy largest-against-largest pass. Never more than n−1 transfers. O(n log n) |
| M4 file input, single or batch | `src/cli.js` | `expenses` may be an array or one object |
| M5 validation | `splitExpense` | percentages = 100, exact sum = total, payer and participants are members, no duplicates, positive amounts with at most 2 decimals. **Every** error in a batch is reported, not just the first |
| E1 rounding | `src/money.js` | all money is integer paise; splits use the largest-remainder method, so ₹100 / 3 = 33.34 + 33.33 + 33.33 |
| E2 zero-activity member | sample `Zoya` | balance ₹0.00 and no settlements |
| E3 payer only for self | sample `e4` | nets to zero and creates no debt |
| Stretch: multi-currency | `src/rates.js` | the expense total is converted once, then re-allocated in the original ratio, so conversion conserves paise too |

## Design notes

- **No floats for money.** Input amounts are converted to integer paise at the edge. `allocate()` uses BigInt internally, so `total × weight` can't overflow.
- **Pure core, thin CLI.** `money`, `rates`, `splitter` and `settle` do no I/O and are unit-tested directly. The CLI only parses arguments, reads files and formats output.
- **Why near-minimum?** Finding the true minimum number of transfers is NP-hard (it reduces to subset-sum). The greedy pass is fast and pairs equal debts first, which covers most real cases.
- **Robustness.** Input files are capped at 5 MB, JSON parse errors are reported cleanly, and member names are length-limited. Internally the code uses `Map`s, so names like `__proto__` are harmless.

## Layout

```
src/   money.js  rates.js  splitter.js  settle.js  cli.js
test/  money / splitter / settle / cli tests (node:test)
data/  expenses.json  rates.json  invalid.json
```
