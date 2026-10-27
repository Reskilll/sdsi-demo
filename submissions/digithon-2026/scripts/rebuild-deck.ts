// Rebuilds the client PowerPoint of a saved run from its trace, without running anything again (no model, no browser).
// Usage: npm run deck:rebuild -- <runId>      -> runs/<runId>/pitch-deck.pptx
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { buildClientDeck } from '../src/agents/clientDeck.js';
import { inferBrandName } from '../src/core/brand.js';
import type { FeedEvent } from '../src/core/events.js';
import type { AuditReport, MatchResult, Prototype, StackReport } from '../src/core/types.js';

const id = process.argv[2];
const dir = join(process.cwd(), 'runs', id ?? '');
if (!id || !existsSync(join(dir, 'trace.json'))) { console.error('Usage: npm run deck:rebuild -- <runId>   (needs runs/<runId>/trace.json)'); process.exit(1); }
const events = JSON.parse(readFileSync(join(dir, 'trace.json'), 'utf8')) as FeedEvent[];
const panel = <T>(name: string) => events.find((e) => e.panel?.name === name)?.panel?.data as T | undefined;
const audit = panel<AuditReport & { title: string; url: string }>('audit');
const match = panel<MatchResult>('team');
if (!audit || !match) { console.error('This run has no audit or team panel, so there is nothing to build a deck from.'); process.exit(1); }
const host = (() => { try { return new URL(audit.url).hostname.replace(/^www\./, ''); } catch { return audit.url; } })();
const brandName = inferBrandName(audit.title, host);
const date = new Date(events[0]?.ts ?? Date.now()).toISOString().slice(0, 10);
const slides = await buildClientDeck({ brandName, url: audit.url, audit, match, prototype: panel<Prototype>('prototype'), stack: panel<StackReport>('stack'), dir, date }, join(dir, 'pitch-deck.pptx'));
console.log(`Wrote runs/${id}/pitch-deck.pptx (${slides} slides) for ${brandName}`);
