import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { PERSONAS, type FeedEvent } from './core/events.js';

// Prints a saved run to the terminal. Reads trace.json only: no model, browser or network.
const root = join(process.cwd(), 'runs');
const arg = process.argv[2];
const fast = process.argv.includes('--fast');

if (!arg || arg === 'list') {
  const rows = readdirSync(root).filter((d) => existsSync(join(root, d, 'trace.json'))).sort((a, b) => statSync(join(root, b)).mtimeMs - statSync(join(root, a)).mtimeMs);
  console.log(rows.length ? 'Replayable runs (newest first):\n' : 'No saved traces yet.');
  for (const id of rows) {
    const t = JSON.parse(readFileSync(join(root, id, 'trace.json'), 'utf8')) as FeedEvent[];
    const audit = t.find((e) => e.panel?.name === 'audit')?.panel?.data as { title?: string; overall?: number } | undefined;
    console.log(`  ${id}  ${(audit?.title ?? '(no audit)').slice(0, 50).padEnd(50)}  score ${audit?.overall ?? '-'}  ${t.length} events`);
  }
  console.log('\nReplay one with: npm run replay -- <id> [--fast]');
  process.exit(0);
}

const file = join(root, arg, 'trace.json');
if (!existsSync(file)) { console.error(`No trace for run "${arg}". Run "npm run replay -- list" to see runs that can be replayed.`); process.exit(1); }
const events = JSON.parse(readFileSync(file, 'utf8')) as FeedEvent[];
for (let i = 0; i < events.length; i++) {
  const e = events[i];
  if (!fast && i > 0) await new Promise((r) => setTimeout(r, Math.max(700, Math.min(e.ts - events[i - 1].ts, 2500))));
  const p = PERSONAS[e.from];
  const to = e.to === 'human' ? ' → a human' : e.to && e.to !== 'all' ? ` → ${PERSONAS[e.to]?.name ?? e.to}` : '';
  console.log(`[${((e.ts - events[0].ts) / 1000).toFixed(1).padStart(6)}s] ${p.emoji} ${p.name}${to}  (${e.kind})  ${e.friendly}`);
  if (e.detail?.summary && /warning|error|status|finding/.test(e.kind)) console.log(`          ${e.detail.summary.split('\n')[0].slice(0, 200)}`);
}
