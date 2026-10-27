import test from 'node:test';
import assert from 'node:assert/strict';
import { handleMcp, TOOLS } from '../core/mcp.js';
import { PERSONAS } from '../core/events.js';

const deps = {
  listRuns: () => [{ id: 'r1', hasTrace: true, url: 'https://x.com', title: 'X', overall: 60 }],
  readTrace: (id: string) => (id === 'r1' ? [{ id: 1, ts: 0, runId: 'r1', from: 'audit' as const, kind: 'partial_result' as const, friendly: '', panel: { name: 'audit', data: { overall: 60, categories: [{ category: 'speed', score: 37 }] } } }] : null),
};
const call = (method: string, params?: Record<string, unknown>, agent: string | null = null) => handleMcp({ jsonrpc: '2.0', id: 1, method, params }, agent, deps) as { result?: Record<string, unknown>; error?: { message: string } };

test('MCP handshake, tool list per agent, and a notification needs no reply', () => {
  assert.equal((call('initialize', { protocolVersion: '2025-06-18' }).result?.capabilities as object) !== undefined, true);
  assert.equal(handleMcp({ jsonrpc: '2.0', method: 'notifications/initialized' }, null, deps), null);
  const names = (call('tools/list', {}, 'speed').result?.tools as { name: string }[]).map((t) => t.name);
  assert.deepEqual(names, ['lead_list_runs', 'speed_get_result']);
  for (const id of Object.keys(PERSONAS)) assert.ok(TOOLS.some((t) => t.agent === id), `every live agent offers a tool: ${id}`);
});

test('tools read saved runs and report errors as tool results', () => {
  const r = call('tools/call', { name: 'speed_get_result', arguments: { run_id: 'r1' } });
  assert.match((r.result?.content as { text: string }[])[0].text, /37/);
  const bad = call('tools/call', { name: 'audit_get_report', arguments: { run_id: '../etc' } });
  assert.equal(bad.result?.isError, true);
  assert.match(call('nope').error!.message, /not found/);
});

test('the Tender Scout triage keeps digital work and drops civil works', () => {
  const t = (title: string) => JSON.parse((call('tools/call', { name: 'tenders_triage', arguments: { title } }).result?.content as { text: string }[])[0].text);
  assert.equal(t('Website revamp and GIGW accessibility audit').relevant, true);
  assert.equal(t('Civil works for depot expansion').relevant, false);
});
