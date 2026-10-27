/**
 * Validation utilities for expense splitting.
 */

const EPSILON = 0.01;

/**
 * Validate that percentages sum to 100 (within epsilon for floating point).
 */
function validatePercentages(shares) {
  const total = shares.reduce((sum, s) => sum + (s.percentage || 0), 0);
  return Math.abs(total - 100) <= EPSILON;
}

/**
 * Validate that exact amounts sum to the total expense amount.
 */
function validateExactAmounts(shares, totalAmount) {
  const sum = shares.reduce((acc, s) => acc + parseFloat(s.amount || 0), 0);
  return Math.abs(sum - parseFloat(totalAmount)) <= EPSILON;
}

/**
 * Compute equal shares, distributing any rounding difference to the first member.
 */
function computeEqualShares(amount, memberIds) {
  const numMembers = memberIds.length;
  const base = Math.floor((amount / numMembers) * 100) / 100; // truncate to 2 decimals
  const remainder = Math.round((amount - base * numMembers) * 100) / 100;

  return memberIds.map((memberId, i) => ({
    memberId,
    amount: i === 0 ? base + remainder : base,
  }));
}

/**
 * Compute percentage-based shares.
 */
function computePercentageShares(amount, shares) {
  return shares.map((s) => ({
    memberId: s.memberId,
    amount: Math.round((amount * s.percentage) / 100 * 100) / 100,
    percentage: s.percentage,
  }));
}

module.exports = {
  validatePercentages,
  validateExactAmounts,
  computeEqualShares,
  computePercentageShares,
  EPSILON,
};