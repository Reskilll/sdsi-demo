// Fixed-rate currency conversion (stretch goal). Rates are read from a file
// such as data/rates.json: { "base": "INR", "rates": { "USD": 83.25, ... } }
// meaning 1 USD = 83.25 INR.

import { allocate } from './money.js';

const CURRENCY_CODE = /^[A-Z]{3}$/;
const RATE_SCALE = 1_000_000; // rates are kept as integers with 6 decimal places

export function parseRates(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('rates file must be a JSON object');
  const { base, rates } = raw;
  if (typeof base !== 'string' || !CURRENCY_CODE.test(base)) throw new Error('rates.base must be a 3-letter currency code');
  if (!rates || typeof rates !== 'object' || Array.isArray(rates)) throw new Error('rates.rates must be an object');

  const table = new Map([[base, RATE_SCALE]]);
  for (const [code, rate] of Object.entries(rates)) {
    if (!CURRENCY_CODE.test(code)) throw new Error(`invalid currency code "${code}" in rates`);
    if (typeof rate !== 'number' || !Number.isFinite(rate) || rate <= 0) {
      throw new Error(`rate for ${code} must be a positive number`);
    }
    table.set(code, Math.round(rate * RATE_SCALE));
  }
  return { base, table };
}

/**
 * Convert per-person shares (minor units of `currency`) into the base currency.
 * The expense total is converted once and then re-allocated in proportion to
 * the original shares, so the converted shares still sum exactly to the
 * converted total — conversion never creates or loses a paisa either.
 */
export function convertShares(shares, currency, rates) {
  if (!rates) {
    throw new Error(`expense is in ${currency} but no rates file was given (use --rates)`);
  }
  if (currency === rates.base) return shares;
  const rate = rates.table.get(currency);
  if (rate === undefined) throw new Error(`no exchange rate for ${currency}`);

  const total = shares.reduce((s, x) => s + x, 0);
  const convertedTotal = Number((BigInt(total) * BigInt(rate) + BigInt(RATE_SCALE / 2)) / BigInt(RATE_SCALE));
  return allocate(convertedTotal, shares);
}
