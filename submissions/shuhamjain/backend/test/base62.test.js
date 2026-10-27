'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { encode, ALPHABET, BASE, MIN_VALUE } = require('../src/lib/base62');

test('base62 alphabet is 62 unique chars', () => {
  assert.strictEqual(ALPHABET.length, BASE);
  assert.strictEqual(new Set(ALPHABET).size, BASE);
});

test('encode(0) is "0" and encode round-trips are reversible', () => {
  assert.strictEqual(encode(0), '0');
  assert.strictEqual(encode(1), '1');
  assert.strictEqual(encode(61), 'Z');

  // Verify reversibility for a spread of values.
  for (const n of [0, 1, 61, 62, 1000, 999999, MIN_VALUE, MIN_VALUE + 5]) {
    const s = encode(n);
    // Manual decode.
    let m = 0;
    for (const ch of s) {
      m = m * BASE + ALPHABET.indexOf(ch);
    }
    assert.strictEqual(m, n, `round-trip mismatch for ${n}`);
  }
});

test('codes start at MIN_VALUE are 6-8 chars', () => {
  const fromCounter = encode(MIN_VALUE);
  assert.ok(fromCounter.length >= 6 && fromCounter.length <= 8);
  // A few million links later still fits.
  assert.ok(encode(MIN_VALUE + 1_000_000).length <= 8);
});

test('encode rejects non-safe / negative integers', () => {
  assert.throws(() => encode(-1), TypeError);
  assert.throws(() => encode(1.5), TypeError);
  assert.throws(() => encode(NaN), TypeError);
});