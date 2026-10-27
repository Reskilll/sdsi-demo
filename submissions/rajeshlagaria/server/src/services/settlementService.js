const { computeBalances } = require('./balanceService');

/**
 * Compute minimal settlement transactions (M3).
 *
 * Greedy min-cash-flow algorithm:
 * 1. Compute net balances (positive = creditor, negative = debtor)
 * 2. Split into creditors and debtors max-heaps
 * 3. Repeatedly pop largest creditor & debtor, settle the smaller amount,
 *    push remainder back until all settled.
 *
 * Returns: Array of { from: string, to: string, amount: number }
 */
async function computeSettlements(groupId) {
  const balances = await computeBalances(groupId);

  // Split into creditors (balance > 0) and debtors (balance < 0)
  const creditors = []; // max-heap (we'll sort descending)
  const debtors = []; // max-heap by abs(debt) descending

  for (const m of balances) {
    const bal = parseFloat(m.balance);
    if (bal > 0.01) {
      creditors.push({ name: m.name, amount: Math.round(bal * 100) / 100 });
    } else if (bal < -0.01) {
      debtors.push({
        name: m.name,
        amount: Math.round(Math.abs(bal) * 100) / 100,
      });
    }
  }

  // Sort descending by amount
  creditors.sort((a, b) => b.amount - a.amount);
  debtors.sort((a, b) => b.amount - a.amount);

  const settlements = [];

  let ci = 0;
  let di = 0;

  while (ci < creditors.length && di < debtors.length) {
    const creditor = creditors[ci];
    const debtor = debtors[di];

    const settleAmount = Math.min(creditor.amount, debtor.amount);
    const rounded = Math.round(settleAmount * 100) / 100;

    if (rounded > 0) {
      settlements.push({
        from: debtor.name,
        to: creditor.name,
        amount: rounded,
      });
    }

    creditor.amount = Math.round((creditor.amount - settleAmount) * 100) / 100;
    debtor.amount = Math.round((debtor.amount - settleAmount) * 100) / 100;

    if (creditor.amount < 0.01) ci++;
    if (debtor.amount < 0.01) di++;
  }

  return settlements;
}

module.exports = { computeSettlements };