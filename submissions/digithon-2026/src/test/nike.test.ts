import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import type { FeedEvent } from '../core/events.js';
import { handleMcp } from '../core/mcp.js';
import { checkDeck, slideTexts } from '../core/deckCheck.js';

// The Nike run is the main demo. These checks keep its saved trace replayable and complete.
const ID = 'mvpmet3q0sc1';
const trace = JSON.parse(readFileSync(`runs/${ID}/trace.json`, 'utf8')) as FeedEvent[];
const panel = (n: string) => trace.find((e) => e.panel?.name === n)?.panel?.data as Record<string, unknown> | undefined;

test('the Nike run replays in order: unique ids, time never runs backwards, ends with done', () => {
  assert.deepEqual(trace.map((e) => e.id), trace.map((_, i) => i + 1));
  for (let i = 1; i < trace.length; i++) assert.ok(trace[i].ts >= trace[i - 1].ts, `event ${i} goes back in time`);
  assert.equal(trace[0].kind, 'plan');
  assert.equal(trace.at(-1)?.kind, 'done');
});

test('the Nike run starts with market research, then has every report section', () => {
  const firstAudit = trace.findIndex((e) => e.from === 'audit'), lastResearch = trace.map((e) => e.from).lastIndexOf('research');
  assert.ok(lastResearch > 0 && lastResearch < firstAudit, 'research comes before the audit');
  for (const n of ['research', 'audit', 'stack', 'team', 'prototype', 'deck']) assert.ok(panel(n), `missing ${n}`);
  assert.equal((panel('audit') as { url: string }).url, 'https://www.nike.in/');
  assert.equal((panel('research') as { company: string }).company, 'Nike India');
});

test('the Nike run can be reused over MCP and its own deck covers the analysis', async () => {
  const deps = { listRuns: () => [{ id: ID, hasTrace: true }], readTrace: (id: string) => (id === ID ? trace : null) };
  const r = handleMcp({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'audit_get_report', arguments: { run_id: ID } } }, 'audit', deps) as { result: { content: { text: string }[] } };
  assert.equal(JSON.parse(r.result.content[0].text).overall, (panel('audit') as { overall: number }).overall);
  if (!existsSync(`runs/${ID}/pitch-deck.pptx`)) return;
  const check = checkDeck(await slideTexts(readFileSync(`runs/${ID}/pitch-deck.pptx`)), { audit: panel('audit') as never, team: panel('team') as never }, 'pitch-deck.pptx');
  assert.ok(check.checks.find((c) => c.item.startsWith('Site score'))?.found, 'the generated deck states the site score');
});
