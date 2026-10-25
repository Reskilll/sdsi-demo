import { test } from 'node:test';
import assert from 'node:assert/strict';
import { allocate, formatMinor, toMinor } from '../src/money.js';

test('E1: ₹100 split 3 ways neither loses nor creates paise', () => {
  const parts = allocate(10000, [1, 1, 1]);
  assert.deepEqual(parts, [3334, 3333, 3333]);
  assert.equal(parts.reduce((a, b) => a + b, 0), 10000);
});

test('allocate always sums to the total for awkward inputs', () => {
  for (const [total, weights] of [
    [1, [1, 1, 1]],
    [999_999, [3333, 3333, 3334]],
    [7, [0, 5, 2]],
    [1_000_000_000_000, [9999, 1]],
  ]) {
    assert.equal(allocate(total, weights).reduce((a, b) => a + b, 0), total);
  }
});

test('allocate gives zero to a zero weight', () => {
  assert.deepEqual(allocate(100, [0, 1]), [0, 100]);
});

test('allocate rejects bad input', () => {
  assert.throws(() => allocate(100, []));
  assert.throws(() => allocate(100, [0, 0]));
  assert.throws(() => allocate(1.5, [1]));
  assert.throws(() => allocate(100, [-1, 2]));
});

test('toMinor converts and validates amounts', () => {
  assert.equal(toMinor(12.5), 1250);
  assert.equal(toMinor(0.1 + 0.2), 30);
  assert.equal(toMinor(0, { allowZero: true }), 0);
  assert.throws(() => toMinor(0), /positive/);
  assert.throws(() => toMinor(-5), /positive/);
  assert.throws(() => toMinor(1.005), /2 decimal/);
  assert.throws(() => toMinor('100'), /finite number/);
  assert.throws(() => toMinor(NaN), /finite number/);
  assert.throws(() => toMinor(1e11), /maximum/);
});

test('formatMinor', () => {
  assert.equal(formatMinor(3334), '₹33.34');
  assert.equal(formatMinor(-5), '-₹0.05');
  assert.equal(formatMinor(100, 'JPY'), 'JPY 1.00');
});
