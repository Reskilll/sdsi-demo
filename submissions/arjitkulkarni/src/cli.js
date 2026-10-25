#!/usr/bin/env node
// Usage: node src/cli.js <expenses.json> [--rates <rates.json>] [--json]

import { readFileSync, statSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { formatMinor } from './money.js';
import { parseRates } from './rates.js';
import { computeBalances, ValidationError } from './splitter.js';
import { simplifyDebts } from './settle.js';

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const USAGE = 'Usage: node src/cli.js <expenses.json> [--rates <rates.json>] [--json]';

function readJson(path) {
  let size;
  try {
    size = statSync(path).size;
  } catch {
    throw new Error(`cannot read file: ${path}`);
  }
  if (size > MAX_FILE_BYTES) throw new Error(`${path} is larger than ${MAX_FILE_BYTES} bytes`);
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    throw new Error(`${path} is not valid JSON: ${e.message}`);
  }
}

export function parseArgs(argv) {
  const opts = { file: null, rates: null, json: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') opts.json = true;
    else if (arg === '--rates') {
      opts.rates = argv[++i];
      if (!opts.rates) throw new Error('--rates needs a file path');
    } else if (arg.startsWith('-')) throw new Error(`unknown option ${arg}`);
    else if (opts.file) throw new Error('only one expenses file may be given');
    else opts.file = arg;
  }
  if (!opts.file) throw new Error('no expenses file given');
  return opts;
}

export function run(argv) {
  const opts = parseArgs(argv);
  const group = readJson(opts.file);
  if (!group || typeof group !== 'object' || Array.isArray(group)) {
    throw new Error('expenses file must be an object with "members" and "expenses"');
  }
  const rates = opts.rates ? parseRates(readJson(opts.rates)) : null;
  const currency = rates?.base ?? 'INR';

  const balances = computeBalances(group, rates);
  const transfers = simplifyDebts(balances);

  if (opts.json) {
    return JSON.stringify(
      {
        currency,
        balances: Object.fromEntries([...balances].map(([m, v]) => [m, v / 100])),
        settlements: transfers.map((t) => ({ ...t, amount: t.amount / 100 })),
      },
      null,
      2,
    );
  }

  const width = Math.max(...[...balances.keys()].map((m) => m.length));
  const lines = ['Net balances (+ is owed, - owes):'];
  for (const [member, amount] of balances) {
    lines.push(`  ${member.padEnd(width)}  ${amount > 0 ? '+' : ''}${formatMinor(amount, currency)}`);
  }
  lines.push('', `Settlements (${transfers.length}):`);
  if (transfers.length === 0) lines.push('  Everyone is settled up.');
  for (const t of transfers) lines.push(`  ${t.from} pays ${t.to} ${formatMinor(t.amount, currency)}`);
  return lines.join('\n');
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(run(process.argv.slice(2)));
  } catch (e) {
    if (e instanceof ValidationError) {
      console.error('Invalid input:');
      for (const msg of e.errors) console.error(`  - ${msg}`);
    } else {
      console.error(`Error: ${e.message}`);
      if (e.message.includes('file given')) console.error(USAGE);
    }
    process.exitCode = 1;
  }
}
