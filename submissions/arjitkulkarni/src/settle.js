// Debt simplification: turn net balances into a short list of
// "A pays B X" transfers.
//
// Finding the true minimum is NP-hard (it reduces to subset-sum), so we use a
// near-minimum greedy that is O(n log n) and never needs more than n - 1
// transfers for n non-zero balances:
//   1. pair any debtor/creditor whose amounts match exactly (1 transfer each);
//   2. settle the rest largest-debtor-against-largest-creditor.

export function simplifyDebts(balances) {
  const debtors = [];
  const creditors = [];
  for (const [member, amount] of balances) {
    if (amount < 0) debtors.push({ member, amount: -amount });
    else if (amount > 0) creditors.push({ member, amount });
  }

  const byAmountThenName = (a, b) => b.amount - a.amount || a.member.localeCompare(b.member);
  debtors.sort(byAmountThenName);
  creditors.sort(byAmountThenName);

  const transfers = [];

  // Pass 1: exact matches.
  const creditorsByAmount = new Map();
  for (const c of creditors) {
    if (!creditorsByAmount.has(c.amount)) creditorsByAmount.set(c.amount, []);
    creditorsByAmount.get(c.amount).push(c);
  }
  for (const d of debtors) {
    const match = creditorsByAmount.get(d.amount)?.shift();
    if (match) {
      transfers.push({ from: d.member, to: match.member, amount: d.amount });
      d.amount = 0;
      match.amount = 0;
    }
  }

  // Pass 2: greedy two-pointer over what is left (both lists stay sorted).
  const ds = debtors.filter((d) => d.amount > 0);
  const cs = creditors.filter((c) => c.amount > 0);
  let i = 0;
  let j = 0;
  while (i < ds.length && j < cs.length) {
    const amount = Math.min(ds[i].amount, cs[j].amount);
    transfers.push({ from: ds[i].member, to: cs[j].member, amount });
    ds[i].amount -= amount;
    cs[j].amount -= amount;
    if (ds[i].amount === 0) i++;
    if (cs[j].amount === 0) j++;
  }

  return transfers;
}
