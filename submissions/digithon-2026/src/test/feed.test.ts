import test from 'node:test';
import assert from 'node:assert/strict';
import { RunBus } from '../core/events.js';
import type { RunContext } from '../core/context.js';
import { defineTool } from '../core/tool.js';
import { salvageHtml } from '../agents/redesign.js';

const run = (): RunContext => ({ runId: 't', url: 'https://x.com', dir: '/tmp', bus: new RunBus('t'), data: {}, startedAt: Date.now(), baseUrl: '', usedStartLines: new Set() });

test('a tool posts a start line, then its result as a separate card post', async () => {
  const tool = defineTool({
    name: 'demo', kind: 'skill',
    feed: { start: ['Starting…'], end: (r: number) => `Got ${r}`, error: 'Failed.', card: (r) => ({ title: 'Demo', headline: `Score ${r}`, score: r, grade: 'B' }) },
    run: async () => 42,
  });
  const r = run();
  await tool({}, { run: r, agent: 'speed' });
  const kinds = r.bus.events.map((e) => e.kind);
  assert.deepEqual(kinds, ['skill_start', 'skill_end']);
  assert.equal(r.bus.events[0].card, undefined);
  assert.equal(r.bus.events[1].card?.score, 42);
  assert.equal(r.bus.events[1].tool?.callId, r.bus.events[0].tool?.callId);
});

test('a failing tool retries once and then reports failure without a card', async () => {
  let calls = 0;
  const tool = defineTool({
    name: 'flaky', feed: { start: ['Go'], end: () => 'ok', error: 'Oops.', card: () => ({ title: 'x', headline: 'x' }) },
    run: async () => { calls++; throw new Error('boom'); },
  });
  const r = run();
  await assert.rejects(tool({}, { run: r, agent: 'speed' }));
  assert.equal(calls, 2);
  assert.ok(r.bus.events.some((e) => e.kind === 'warning'));
  assert.equal(r.bus.events.at(-1)?.card, undefined);
});

test('salvage closes a page cut off mid-body but rejects one cut off in the styles', () => {
  const css = '<style>' + 'a{color:red}'.repeat(300) + '</style>';
  const cutBody = `<!doctype html><html><head>${css}</head><body><main><section><h1>Hi</h1><p>text that was being wri`;
  const ok = salvageHtml(cutBody + ' '.repeat(10));
  assert.ok(ok && ok.endsWith('</html>') && ok.includes('<h1>Hi</h1>'));
  assert.equal(salvageHtml('<!doctype html><html><head><style>' + 'a{color:red}'.repeat(400)), null);
  assert.equal(salvageHtml('<!doctype html><html><body>tiny'), null);
});
