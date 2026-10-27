// Puts the Market Researcher's posts into a saved run, so a replay starts with the latest news on the company.
// Usage: npm run research:add -- <runId>     (the brief comes from config/research/*.json, matched on the run's website)
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { loadBrief, withResearch } from '../src/agents/research.js';
import type { FeedEvent } from '../src/core/events.js';

const id = process.argv[2];
const file = join(process.cwd(), 'runs', id ?? '', 'trace.json');
if (!id || !existsSync(file)) { console.error('Usage: npm run research:add -- <runId>   (needs runs/<runId>/trace.json)'); process.exit(1); }
const trace = JSON.parse(readFileSync(file, 'utf8')) as FeedEvent[];
const url = (trace.find((e) => e.panel?.name === 'audit')?.panel?.data as { url?: string } | undefined)?.url ?? trace[0]?.friendly.match(/for (\S+?)\.\s/)?.[1] ?? '';
const brief = loadBrief(url);
if (!brief) { console.error(`No research brief in config/research/ matches ${url || 'this run'}.`); process.exit(1); }
writeFileSync(file, JSON.stringify(withResearch(trace, brief)));
console.log(`Added ${brief.items.length} research signals for ${brief.company} to runs/${id}/trace.json`);
