import test from 'node:test';
import assert from 'node:assert/strict';
import { RunBus } from '../core/events.js';
import type { RunContext } from '../core/context.js';
import { costOf } from '../core/llm.js';
import { executePlan } from '../agents/lead.js';
import { RulePlanner } from '../agents/planner.js';

test('cost uses list prices, with cache writes at 1.25x and reads at 0.1x input', () => {
  // claude-sonnet-5-5: $2 in, $10 out per million tokens.
  assert.equal(costOf('claude-sonnet-5-5', { input: 1_000_000, output: 0, cacheRead: 0, cacheWrite: 0 }), 2);
  assert.equal(costOf('claude-sonnet-5-5', { input: 0, output: 1_000_000, cacheRead: 0, cacheWrite: 0 }), 10);
  assert.equal(costOf('claude-sonnet-5-5', { input: 0, output: 0, cacheRead: 1_000_000, cacheWrite: 1_000_000 }), 0.2 + 2.5);
  assert.equal(costOf('some-unknown-model', { input: 1, output: 1, cacheRead: 0, cacheWrite: 0 }), null);
});

test('the lead posts the run total when model calls were made', async () => {
  const run: RunContext = { runId: 't', url: 'https://example.com', dir: '/tmp', bus: new RunBus('t'), data: {}, startedAt: Date.now(), baseUrl: '', usedStartLines: new Set() };
  const step = (id: string, tokens: number) => async (r: RunContext) => {
    if (id === 'audit') r.data.audit = { overall: 60, grade: 'C', categories: [{ category: 'mobile', score: 40 }], topFixes: [] } as never;
    if (id === 'redesign') { r.data.brand = {} as never; r.data.prototype = { reaudit: [] } as never; }
    if (id === 'bench') r.data.match = {} as never;
    if (tokens) r.bus.emit({ from: 'ux', kind: 'usage', friendly: '', usage: { model: 'claude-sonnet-5-5', input: tokens, output: 0, cacheRead: 0, cacheWrite: 0, costUsd: costOf('claude-sonnet-5-5', { input: tokens, output: 0, cacheRead: 0, cacheWrite: 0 }) } });
  };
  await executePlan(run, new RulePlanner(), { audit: step('audit', 500_000), redesign: step('redesign', 500_000), bench: step('bench', 0), deck: step('deck', 0) });
  const total = run.bus.events.find((e) => e.stat?.label.startsWith('model cost'));
  assert.ok(total, 'a total post is emitted');
  assert.equal(total.stat?.value, '$2.000');
  assert.ok(run.bus.events.indexOf(total) < run.bus.events.findIndex((e) => e.kind === 'done'), 'posted before done');
});
