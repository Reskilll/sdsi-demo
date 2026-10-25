import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cli = (...args) => spawnSync(process.execPath, [join(root, 'src/cli.js'), ...args], { cwd: root, encoding: 'utf8' });

test('M4: processes the sample batch end to end (JSON output)', () => {
  const r = cli('data/expenses.json', '--rates', 'data/rates.json', '--json');
  assert.equal(r.status, 0, r.stderr);
  const out = JSON.parse(r.stdout);
  assert.equal(out.currency, 'INR');
  assert.equal(out.balances.Zoya, 0); // E2
  const total = Object.values(out.balances).reduce((a, b) => a + Math.round(b * 100), 0);
  assert.equal(total, 0);
  assert.ok(out.settlements.length <= 3);
});

test('human-readable output lists balances and settlements', () => {
  const r = cli('data/expenses.json', '--rates', 'data/rates.json');
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /Net balances/);
  assert.match(r.stdout, / pays /);
});

test('invalid sample reports every error and exits 1', () => {
  const r = cli('data/invalid.json');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /percentages sum to 80/);
  assert.match(r.stderr, /exact shares sum to 400 but the total is 500/);
  assert.match(r.stderr, /payer "Stranger" is not a group member/);
});

test('bad arguments and missing files fail cleanly', () => {
  assert.match(cli().stderr, /no expenses file given/);
  assert.match(cli('nope.json').stderr, /cannot read file/);
  assert.match(cli('data/expenses.json', '--wat').stderr, /unknown option/);
  assert.match(cli('data/expenses.json').stderr, /no rates file/);
});
