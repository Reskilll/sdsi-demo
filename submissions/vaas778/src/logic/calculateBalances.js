/**
 * calculateBalances.js — Compute net balances for all members.
 *
 * Net balance = total paid - total owed (in paise).
 * Positive = owed money, Negative = owes money.
 */

/**
 * @param {Array<{ id: string }>} members
 * @param {Array<{ paidBy: string, shares: Record<string, number> }>} expenses
 *   shares is { memberId: paiseOwed }.
 * @returns {Array<{ memberId: string, paid: number, owed: number, balance: number }>}
 */
export function calculateBalances(members, expenses) {
  // Initialize all members with zero
  const balanceMap = new Map();
  for (const m of members) {
    balanceMap.set(m.id, { memberId: m.id, paid: 0, owed: 0, balance: 0 });
  }

  for (const exp of expenses) {
    // Credit the payer
    const payerEntry = balanceMap.get(exp.paidBy);
    if (payerEntry) {
      payerEntry.paid += exp.amountPaise;
      payerEntry.balance += exp.amountPaise;
    }

    // Debit each participant
    for (const [pid, share] of Object.entries(exp.shares)) {
      const entry = balanceMap.get(pid);
      if (entry) {
        entry.owed += share;
        entry.balance -= share;
      }
    }
  }

  // Return sorted by memberId for determinism
  const result = [...balanceMap.values()];
  result.sort((a, b) => a.memberId.localeCompare(b.memberId));
  return result;
}

/**
 * Verify that total balance across all entries equals zero.
 * Returns true within rounding tolerance.
 */
export function verifyBalancesZero(balances) {
  const total = balances.reduce((sum, b) => sum + b.balance, 0);
  return total === 0;
}