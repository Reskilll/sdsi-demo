// Core domain: validate expenses, split them into per-member shares and
// compute each member's net balance. Everything here is pure (no I/O).

import { allocate, toMinor } from './money.js';
import { convertShares } from './rates.js';

const MAX_NAME_LENGTH = 50;
const SPLIT_TYPES = new Set(['equal', 'exact', 'percentage']);

export class ValidationError extends Error {
  constructor(errors) {
    super(errors.join('\n'));
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

export function parseMembers(members) {
  if (!Array.isArray(members) || members.length === 0) {
    throw new ValidationError(['"members" must be a non-empty array of names']);
  }
  const errors = [];
  const seen = new Set();
  for (const name of members) {
    if (typeof name !== 'string' || name.trim() === '' || name.length > MAX_NAME_LENGTH) {
      errors.push(`member name ${JSON.stringify(name)} must be a non-empty string of at most ${MAX_NAME_LENGTH} chars`);
    } else if (seen.has(name)) {
      errors.push(`duplicate member "${name}"`);
    } else {
      seen.add(name);
    }
  }
  if (errors.length) throw new ValidationError(errors);
  return [...seen];
}

/**
 * Validate one expense and return its shares as [{ member, share }] in the
 * expense's own currency (minor units). Throws ValidationError listing every
 * problem found, not just the first.
 */
export function splitExpense(expense, memberSet) {
  const label = `expense ${JSON.stringify(expense?.id ?? expense?.description ?? '?')}`;
  const errors = [];
  const fail = (msg) => errors.push(`${label}: ${msg}`);

  if (!expense || typeof expense !== 'object' || Array.isArray(expense)) {
    throw new ValidationError([`${label}: must be an object`]);
  }

  const { paidBy, amount, split } = expense;
  if (!memberSet.has(paidBy)) fail(`payer ${JSON.stringify(paidBy)} is not a group member`);

  let total;
  try {
    total = toMinor(amount);
  } catch (e) {
    fail(e.message);
  }

  if (!split || typeof split !== 'object' || !SPLIT_TYPES.has(split.type)) {
    fail(`split.type must be one of ${[...SPLIT_TYPES].join(', ')}`);
    throw new ValidationError(errors);
  }

  // Normalise the three split types into (members, integer weights or exact amounts).
  let entries;
  if (split.type === 'equal') {
    const among = split.among ?? [...memberSet];
    if (!Array.isArray(among) || among.length === 0) fail('split.among must be a non-empty array');
    else entries = among.map((m) => [m, 1]);
  } else {
    if (!split.shares || typeof split.shares !== 'object' || Array.isArray(split.shares)) {
      fail('split.shares must be an object of { member: value }');
    } else {
      entries = Object.entries(split.shares);
      if (entries.length === 0) fail('split.shares must not be empty');
    }
  }

  if (entries) {
    const seen = new Set();
    for (const [m] of entries) {
      if (!memberSet.has(m)) fail(`participant ${JSON.stringify(m)} is not a group member`);
      if (seen.has(m)) fail(`participant "${m}" listed twice`);
      seen.add(m);
    }
  }

  let shares;
  if (entries && errors.length === 0) {
    const members = entries.map(([m]) => m);
    if (split.type === 'equal') {
      shares = allocate(total, entries.map(() => 1));
    } else if (split.type === 'exact') {
      const values = [];
      for (const [m, v] of entries) {
        try {
          values.push(toMinor(v, { allowZero: true }));
        } catch (e) {
          fail(`exact share for ${m}: ${e.message}`);
        }
      }
      const sum = values.reduce((a, b) => a + b, 0);
      if (errors.length === 0 && sum !== total) {
        fail(`exact shares sum to ${sum / 100} but the total is ${total / 100}`);
      }
      shares = values;
    } else {
      // Percentages may carry up to 2 decimals (33.33%), so work in hundredths of a percent.
      const basisPoints = [];
      for (const [m, v] of entries) {
        if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 100) {
          fail(`percentage for ${m} must be a number between 0 and 100`);
          continue;
        }
        const bp = Math.round(v * 100);
        if (Math.abs(v * 100 - bp) > 1e-6) fail(`percentage for ${m} has more than 2 decimal places`);
        basisPoints.push(bp);
      }
      const sum = basisPoints.reduce((a, b) => a + b, 0);
      if (errors.length === 0 && sum !== 10000) fail(`percentages sum to ${sum / 100}, expected 100`);
      if (errors.length === 0) shares = allocate(total, basisPoints);
    }
    if (errors.length === 0) {
      return members.map((member, i) => ({ member, share: shares[i] }));
    }
  }
  throw new ValidationError(errors);
}

/**
 * Process a whole group: validate every expense (collecting all errors),
 * convert to the base currency and return net balances in minor units.
 * Positive balance = is owed money; negative = owes money.
 */
export function computeBalances({ members, expenses }, rates = null) {
  const memberList = parseMembers(members);
  const memberSet = new Set(memberList);
  const list = Array.isArray(expenses) ? expenses : expenses ? [expenses] : [];

  const balances = new Map(memberList.map((m) => [m, 0]));
  const errors = [];
  const ids = new Set();

  list.forEach((expense, i) => {
    try {
      if (expense?.id !== undefined) {
        if (ids.has(expense.id)) throw new ValidationError([`duplicate expense id ${JSON.stringify(expense.id)}`]);
        ids.add(expense.id);
      }
      const currency = expense?.currency ?? rates?.base ?? 'INR';
      const raw = splitExpense(expense, memberSet);
      const base = currency === (rates?.base ?? 'INR')
        ? raw.map((r) => r.share)
        : convertShares(raw.map((r) => r.share), currency, rates);
      const paid = base.reduce((a, b) => a + b, 0);

      balances.set(expense.paidBy, balances.get(expense.paidBy) + paid);
      raw.forEach(({ member }, j) => balances.set(member, balances.get(member) - base[j]));
    } catch (e) {
      const msgs = e instanceof ValidationError ? e.errors : [e.message];
      errors.push(...msgs.map((msg) => `#${i + 1} ${msg}`));
    }
  });

  if (errors.length) throw new ValidationError(errors);

  const net = [...balances.values()].reduce((a, b) => a + b, 0);
  if (net !== 0) throw new Error(`internal error: balances sum to ${net}, expected 0`);
  return balances;
}
