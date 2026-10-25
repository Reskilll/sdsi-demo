import { test } from 'node:test';
import assert from 'node:assert/strict';
import { simplifyDebts } from '../src/settle.js';

const toMap = (obj) => new Map(Object.entries(obj));

/** Apply transfers to balances and assert everyone ends at exactly zero. */
function assertSettles(balances, transfers) {
  const left = new Map(balances);
  for (const { from, to, amount } of transfers) {
    assert.ok(amount > 0, 'transfers must be positive');
    left.set(from, left.get(from) + amount);
    left.set(to, left.get(to) - amount);
  }
  for (const [m, v] of left) assert.equal(v, 0, `${m} is not settled`);
}

test('M3: chain of debts collapses into one transfer', () => {
  // A owes B 100, B owes C 100  ->  A pays C 100
  const balances = toMap({ A: -100, B: 0, C: 100 });
  const t = simplifyDebts(balances);
  assert.deepEqual(t, [{ from: 'A', to: 'C', amount: 100 }]);
});

test('M3: exact matches are paired first', () => {
  const balances = toMap({ A: -500, B: -300, C: 300, D: 500 });
  const t = simplifyDebts(balances);
  assert.equal(t.length, 2);
  assertSettles(balances, t);
});

test('M3: never more than n-1 transfers and always settles', () => {
  let seed = 42;
  const rand = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
  for (let round = 0; round < 200; round++) {
    const n = 2 + Math.floor(rand() * 10);
    const values = Array.from({ length: n - 1 }, () => Math.floor(rand() * 20000) - 10000);
    values.push(-values.reduce((a, b) => a + b, 0));
    const balances = new Map(values.map((v, i) => [`m${i}`, v]));
    const t = simplifyDebts(balances);
    const nonZero = values.filter((v) => v !== 0).length;
    assert.ok(t.length <= Math.max(0, nonZero - 1), `${t.length} transfers for ${nonZero} people`);
    assertSettles(balances, t);
  }
});

test('E2: zero balances produce no transfers', () => {
  assert.deepEqual(simplifyDebts(toMap({ A: 0, B: 0 })), []);
});

test('performance: 10,000 members settle quickly', () => {
  const balances = new Map();
  for (let i = 0; i < 5000; i++) {
    balances.set(`d${i}`, -(i + 1));
    balances.set(`c${i}`, i + 1);
  }
  const start = performance.now();
  const t = simplifyDebts(balances);
  assert.ok(performance.now() - start < 1000);
  assert.equal(t.length, 5000);
  assertSettles(balances, t);
});
