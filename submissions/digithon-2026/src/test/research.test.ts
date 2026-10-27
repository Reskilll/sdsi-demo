import test from 'node:test';
import assert from 'node:assert/strict';
import { loadBrief, researchEvents, withResearch } from '../agents/research.js';
import { executePlan } from '../agents/lead.js';
import { RulePlanner } from '../agents/planner.js';
import { RunBus } from '../core/events.js';
import type { RunContext } from '../core/context.js';

test('a brief is found by the website it belongs to, and not for other sites', () => {
  assert.equal(loadBrief('https://www.nike.in/')?.company, 'Nike India');
  assert.equal(loadBrief('nike.com')?.company, 'Nike India');
  assert.equal(loadBrief('https://example.com'), null);
  assert.equal(loadBrief('https://notnike.in'), null, 'a different domain that only ends with the same letters does not match');
});

test('research posts each signal with what we can do, then a summary for the Coordinator', () => {
  const b = loadBrief('nike.in')!;
  const evs = researchEvents(b).map((x) => x.ev);
  assert.equal(evs.filter((e) => e.kind === 'finding').length, b.items.length);
  assert.ok(evs.every((e) => e.kind !== 'finding' || String(e.card?.metrics?.['What we can do']).length > 0));
  assert.equal(evs.find((e) => e.panel)?.panel?.name, 'research');
  assert.equal(evs.at(-1)?.to, 'lead');
});

test('adding research to a saved trace goes after the opening post and can run twice', () => {
  const b = loadBrief('nike.in')!;
  const trace = [0, 1000, 5000].map((t, i) => ({ id: i + 1, ts: 1e12 + t, runId: 'r', from: i ? 'audit' : 'lead', kind: 'status', friendly: '' }));
  const once = withResearch(trace, b), twice = withResearch(once, b);
  assert.deepEqual(twice, once);
  assert.equal(once[0].from, 'lead');
  assert.equal(once[1].from, 'lead'); assert.equal(once[2].from, 'research');
  assert.deepEqual(once.map((e) => e.id), once.map((_, i) => i + 1));
  for (let i = 1; i < once.length; i++) assert.ok(once[i].ts >= once[i - 1].ts, 'time never runs backwards');
  assert.equal(once.at(-1)!.ts - once.at(-2)!.ts, 4000, 'the gaps between the original posts are kept');
});

test('a live run starts with research when a brief exists', async () => {
  const run: RunContext = { runId: 't', url: 'https://www.nike.in/', dir: '/tmp', bus: new RunBus('t'), data: {}, startedAt: Date.now(), baseUrl: '', usedStartLines: new Set() };
  const done = async (r: RunContext) => { r.data.audit = { overall: 60, grade: 'D', categories: [], topFixes: [] } as never; r.data.brand = {} as never; r.data.match = {} as never; };
  const orig = setTimeout; (globalThis as { setTimeout: unknown }).setTimeout = (f: () => void) => orig(f, 0); // skip the pauses
  try { await executePlan(run, new RulePlanner(), { audit: done, redesign: done, bench: done, deck: done }); } finally { (globalThis as { setTimeout: unknown }).setTimeout = orig; }
  const firstResearch = run.bus.events.findIndex((e) => e.from === 'research'), firstStep = run.bus.events.findIndex((e) => e.from === 'lead' && e.kind === 'status');
  assert.ok(firstResearch > 0 && firstResearch < firstStep, 'research comes before the Coordinator picks the first step');
  assert.equal(run.data.research?.company, 'Nike India');
});
