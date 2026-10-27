/**
 * Currency utility functions.
 * All internal currency values are integers representing paise (1/100 of ₹).
 * Display functions format to ₹ with two decimal places.
 */

/** Convert rupees (number) to paise (integer). */
export function rupeesToPaise(rupees) {
  if (typeof rupees !== 'number' || !isFinite(rupees)) {
    throw new Error(`Invalid rupee amount: ${rupees}`);
  }
  return Math.round(rupees * 100);
}

/** Convert paise (integer) to rupees display string "₹X,XXX.XX". */
export function paiseToRupees(paise) {
  if (!Number.isInteger(paise)) {
    throw new Error(`Paise must be an integer, got: ${paise}`);
  }
  const rupees = paise / 100;
  return '₹' + rupees.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Format a signed paise value for display, e.g. "+₹1,500.00" or "-₹250.00". */
export function formatSignedBalance(paise) {
  if (!Number.isInteger(paise)) {
    throw new Error(`Paise must be an integer, got: ${paise}`);
  }
  if (paise === 0) return paiseToRupees(0);
  const sign = paise > 0 ? '+' : '-';
  return sign + paiseToRupees(Math.abs(paise));
}

/** Format paise as a plain number string with 2 decimals, no currency symbol. */
export function paiseToDecimal(paise) {
  return (paise / 100).toFixed(2);
}