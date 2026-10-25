import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeBalances, ValidationError } from '../src/splitter.js';
import { parseRates } from '../src/rates.js';

const members = ['A', 'B', 'C', 'D'];
const balancesOf = (expenses, rates) => Object.fromEntries(computeBalances({ members, expenses }, rates));

test('M1: equal split', () => {
  const b = balancesOf([{ paidBy: 'A', amount: 90, split: { type: 'equal', among: ['A', 'B', 'C'] } }]);
  assert.deepEqual(b, { A: 6000, B: -3000, C: -3000, D: 0 });
});

test('M1: equal split defaults to every member', () => {
  const b = balancesOf([{ paidBy: 'A', amount: 100, split: { type: 'equal' } }]);
  assert.deepEqual(b, { A: 7500, B: -2500, C: -2500, D: -2500 });
});

test('M1: exact split', () => {
  const b = balancesOf([{ paidBy: 'B', amount: 100.5, split: { type: 'exact', shares: { A: 60.5, B: 40 } } }]);
  assert.deepEqual(b, { A: -6050, B: 6050, C: 0, D: 0 });
});

test('M1: percentage split with decimals keeps every paisa', () => {
  const b = balancesOf([
    { paidBy: 'C', amount: 100, split: { type: 'percentage', shares: { A: 33.33, B: 33.33, C: 33.34 } } },
  ]);
  assert.deepEqual(b, { A: -3333, B: -3333, C: 6666, D: 0 });
});

test('E1: ₹100 split 3 ways — balances still sum to zero', () => {
  const b = balancesOf([{ paidBy: 'A', amount: 100, split: { type: 'equal', among: ['A', 'B', 'C'] } }]);
  assert.equal(Object.values(b).reduce((x, y) => x + y, 0), 0);
  assert.deepEqual(b, { A: 6666, B: -3333, C: -3333, D: 0 });
});

test('E2: member with zero activity has a zero balance', () => {
  const b = balancesOf([{ paidBy: 'A', amount: 10, split: { type: 'equal', among: ['A', 'B'] } }]);
  assert.equal(b.D, 0);
});

test('E3: payer paying only for themselves nets to zero', () => {
  const b = balancesOf([{ paidBy: 'A', amount: 450, split: { type: 'equal', among: ['A'] } }]);
  assert.deepEqual(b, { A: 0, B: 0, C: 0, D: 0 });
});

test('M4: a single expense object (not an array) is accepted', () => {
  const b = Object.fromEntries(
    computeBalances({ members, expenses: { paidBy: 'A', amount: 20, split: { type: 'equal', among: ['A', 'B'] } } }),
  );
  assert.deepEqual(b, { A: 1000, B: -1000, C: 0, D: 0 });
});

test('no expenses gives all-zero balances', () => {
  assert.deepEqual(balancesOf([]), { A: 0, B: 0, C: 0, D: 0 });
});

function errorsOf(expenses, extra = {}) {
  try {
    computeBalances({ members, expenses, ...extra });
  } catch (e) {
    assert.ok(e instanceof ValidationError, e.message);
    return e.errors.join('\n');
  }
  assert.fail('expected a ValidationError');
}

test('M5: percentages must sum to 100', () => {
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'percentage', shares: { A: 50, B: 40 } } }]), /sum to 90, expected 100/);
});

test('M5: exact amounts must sum to the total', () => {
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'exact', shares: { A: 5, B: 4 } } }]), /sum to 9 but the total is 10/);
});

test('M5: payer must be a group member', () => {
  assert.match(errorsOf([{ paidBy: 'Z', amount: 10, split: { type: 'equal' } }]), /payer "Z" is not a group member/);
});

test('M5: participants must be group members and not repeated', () => {
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'equal', among: ['A', 'Z'] } }]), /participant "Z"/);
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'equal', among: ['A', 'A'] } }]), /listed twice/);
});

test('M5: other malformed input is rejected', () => {
  assert.match(errorsOf([{ paidBy: 'A', amount: -1, split: { type: 'equal' } }]), /positive/);
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'thirds' } }]), /split.type/);
  assert.match(errorsOf([{ paidBy: 'A', amount: 10, split: { type: 'percentage', shares: { A: 150 } } }]), /between 0 and 100/);
  assert.match(errorsOf([{ id: 1, paidBy: 'A', amount: 1, split: { type: 'equal' } }, { id: 1, paidBy: 'A', amount: 1, split: { type: 'equal' } }]), /duplicate expense id/);
  assert.match(errorsOf([], { members: ['A', 'A'] }), /duplicate member/);
  assert.match(errorsOf([], { members: [] }), /non-empty array/);
});

test('M5: every invalid expense in a batch is reported, not just the first', () => {
  const msg = errorsOf([
    { paidBy: 'Z', amount: 10, split: { type: 'equal' } },
    { paidBy: 'A', amount: 10, split: { type: 'exact', shares: { A: 1 } } },
  ]);
  assert.match(msg, /#1 .*payer/);
  assert.match(msg, /#2 .*exact shares/);
});

test('stretch: foreign-currency expense converts with fixed rates and conserves paise', () => {
  const rates = parseRates({ base: 'INR', rates: { USD: 83.25 } });
  const b = balancesOf([{ paidBy: 'A', amount: 9, currency: 'USD', split: { type: 'equal', among: ['A', 'B', 'C'] } }], rates);
  // $9 = ₹749.25 = 74925 paise -> 24975 each
  assert.deepEqual(b, { A: 49950, B: -24975, C: -24975, D: 0 });
  // $10 / 3 is uneven ($3.34, $3.33, $3.33): ₹832.50 is split in that ratio, still summing exactly
  const uneven = balancesOf([{ paidBy: 'A', amount: 10, currency: 'USD', split: { type: 'equal', among: ['A', 'B', 'C'] } }], rates);
  assert.deepEqual(uneven, { A: 55444, B: -27722, C: -27722, D: 0 });
});

test('stretch: unknown currency or missing rates file is an error', () => {
  const rates = parseRates({ base: 'INR', rates: { USD: 83.25 } });
  const exp = [{ paidBy: 'A', amount: 10, currency: 'XYZ', split: { type: 'equal' } }];
  assert.throws(() => computeBalances({ members, expenses: exp }, rates), /no exchange rate for XYZ/);
  assert.throws(() => computeBalances({ members, expenses: [{ ...exp[0], currency: 'USD' }] }), /no rates file/);
});

test('parseRates validates the file', () => {
  assert.throws(() => parseRates({ base: 'inr', rates: {} }), /3-letter/);
  assert.throws(() => parseRates({ base: 'INR', rates: { USD: -1 } }), /positive/);
  assert.throws(() => parseRates([]), /JSON object/);
});
