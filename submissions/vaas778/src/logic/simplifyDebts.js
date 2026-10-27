/**
 * simplifyDebts.js — Greedy debt simplification algorithm.
 *
 * Given net balances (in paise), generates a near-minimal set of settlement
 * transactions that settle all debts.
 *
 * Algorithm: Greedy matching of largest creditor with largest debtor.
 *   - Sort creditors (positive balance) descending.
 *   - Sort debtors (negative balance) by absolute value descending.
 *   - At each step, settle between the largest creditor and largest debtor
 *     for the min of their absolute values.
 *   - Repeat until all balances are zero.
 *
 * This is a 2-approximation of the minimum number of transactions.
 * It is deterministic for identical inputs (tie-breaking by member ID).
 *
 * @returns {Array<{ from: string, to: string, amount: number }>}
 *   from = debtor (who pays), to = creditor (who receives), amount in paise.
 */

/**
 * @param {Array<{ memberId: string, balance: number }>} balances
 * @returns {Array<{ from: string, to: string, amount: number }>}
 */
export function simplifyDebts(balances) {
  // Separate creditors and debtors, skip zero-balance members
  const creditors = [];
  const debtors = [];

  for (const b of balances) {
    if (b.balance > 0) {
      creditors.push({ memberId: b.memberId, amount: b.balance });
    } else if (b.balance < 0) {
      debtors.push({ memberId: b.memberId, amount: -b.balance });
    }
    // Zero balance — ignore
  }

  // Sort descending by amount, tie-break by memberId for determinism
  const sortDesc = (a, b) => b.amount - a.amount || a.memberId.localeCompare(b.memberId);
  creditors.sort(sortDesc);
  debtors.sort(sortDesc);

  const settlements = [];
  let ci = 0;
  let di = 0;

  while (ci < creditors.length && di < debtors.length) {
    const creditor = creditors[ci];
    const debtor = debtors[di];
    const settleAmount = Math.min(creditor.amount, debtor.amount);

    if (settleAmount > 0) {
      settlements.push({
        from: debtor.memberId,
        to: creditor.memberId,
        amount: settleAmount,
      });

      creditor.amount -= settleAmount;
      debtor.amount -= settleAmount;
    }

    if (creditor.amount === 0) ci++;
    if (debtor.amount === 0) di++;
  }

  return settlements;
}

/**
 * Verify that applying the settlements results in zero balances for all members.
 * @param {Array<{ memberId: string, balance: number }>} originalBalances
 * @param {Array<{ from: string, to: string, amount: number }>} settlements
 * @returns {boolean}
 */
export function verifySettlements(originalBalances, settlements) {
  const remaining = new Map();
  for (const b of originalBalances) {
    remaining.set(b.memberId, b.balance);
  }

  for (const s of settlements) {
    const fromBal = remaining.get(s.from) || 0;
    const toBal = remaining.get(s.to) || 0;
    remaining.set(s.from, fromBal + s.amount); // debtor pays: balance increases (less negative)
    remaining.set(s.to, toBal - s.amount); // creditor receives: balance decreases
  }

  for (const bal of remaining.values()) {
    if (bal !== 0) return false;
  }
  return true;
}