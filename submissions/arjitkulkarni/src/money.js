// All money is handled as integer minor units (paise) so no rounding error
// can ever create or lose a paisa. Floats only appear at the input boundary.

const MAX_MAJOR_UNITS = 1e10; // sanity cap: ₹10,000,000,000 per expense

/**
 * Convert a major-unit amount (e.g. 12.5 rupees) to integer minor units (1250 paise).
 * Rejects non-numbers, non-positive values and more than 2 decimal places.
 */
export function toMinor(amount, { allowZero = false } = {}) {
  if (typeof amount !== 'number' || !Number.isFinite(amount)) {
    throw new Error(`amount must be a finite number, got ${JSON.stringify(amount)}`);
  }
  if (amount < 0 || (!allowZero && amount === 0)) {
    throw new Error(`amount must be ${allowZero ? 'non-negative' : 'positive'}, got ${amount}`);
  }
  if (amount > MAX_MAJOR_UNITS) {
    throw new Error(`amount ${amount} exceeds the maximum of ${MAX_MAJOR_UNITS}`);
  }
  const minor = Math.round(amount * 100);
  if (Math.abs(amount * 100 - minor) > 1e-6) {
    throw new Error(`amount ${amount} has more than 2 decimal places`);
  }
  return minor;
}

/**
 * Split `total` minor units in proportion to integer `weights` using the
 * largest-remainder method. The result always sums exactly to `total`.
 * Ties on the remainder go to the earlier index, so output is deterministic.
 * BigInt is used so total * weight can never overflow.
 */
export function allocate(total, weights) {
  if (!Number.isInteger(total) || total < 0) throw new Error('total must be a non-negative integer');
  if (weights.length === 0) throw new Error('cannot allocate among zero weights');
  if (weights.some((w) => !Number.isInteger(w) || w < 0)) throw new Error('weights must be non-negative integers');
  const weightSum = weights.reduce((a, b) => a + b, 0);
  if (weightSum === 0) throw new Error('weights must not all be zero');

  const T = BigInt(total);
  const W = BigInt(weightSum);
  const parts = weights.map((w, index) => {
    const numerator = T * BigInt(w);
    return { index, base: numerator / W, remainder: numerator % W };
  });

  let leftover = total - parts.reduce((s, p) => s + Number(p.base), 0);
  const byRemainder = [...parts].sort((a, b) =>
    a.remainder === b.remainder ? a.index - b.index : a.remainder > b.remainder ? -1 : 1,
  );
  const result = parts.map((p) => Number(p.base));
  for (let i = 0; leftover > 0; i++, leftover--) result[byRemainder[i].index] += 1;
  return result;
}

const SYMBOLS = { INR: '₹', USD: '$', EUR: '€', GBP: '£' };

/** Format minor units for display, e.g. 123456 -> "₹1234.56". */
export function formatMinor(minor, currency = 'INR') {
  const sign = minor < 0 ? '-' : '';
  const abs = Math.abs(minor);
  const major = Math.floor(abs / 100);
  const cents = String(abs % 100).padStart(2, '0');
  const symbol = SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${major}.${cents}`;
}
