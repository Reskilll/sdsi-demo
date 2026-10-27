import test from 'node:test';
import assert from 'node:assert/strict';
import { RunBus } from '../core/events.js';
import type { RunContext } from '../core/context.js';
import { executePlan, type Runners } from '../agents/lead.js';
import { LlmPlanner, RulePlanner, validateDecision, type PlanState, type StepId } from '../agents/planner.js';

function fakeRun(): RunContext {
  return { runId: 't', url: 'https://example.com', dir: '/tmp', bus: new RunBus('t'), data: {}, startedAt: Date.now(), baseUrl: '', usedStartLines: new Set() };
}

/** Fake runners record the order they were called and populate just enough run data for the planner's facts. */
function fakeRunners(log: StepId[], opts: { fail?: StepId[]; regress?: boolean } = {}): Runners {
  const step = (id: StepId, fn?: (run: RunContext) => void) => async (run: RunContext) => {
    log.push(id);
    if (opts.fail?.includes(id)) throw new Error(`${id} boom`);
    fn?.(run);
  };
  return {
    audit: step('audit', (r) => { r.data.audit = { overall: 60, grade: 'C', categories: [{ category: 'mobile', score: 40 }], topFixes: [{ title: 'Fix A' }] } as never; }),
    redesign: step('redesign', (r) => { r.data.brand = {} as never; r.data.prototype = { reaudit: [{ category: 'mobile', before: 50, after: opts.regress && log.filter((x) => x === 'redesign').length === 1 ? 30 : 80 }] } as never; }),
    bench: step('bench', (r) => { r.data.match = {} as never; }),
    deck: step('deck'),
  };
}

const scripted = (answers: (string | Error | null)[]) => { let i = 0; return async () => { const a = answers[i++]; if (a instanceof Error) throw a; return a ?? null; }; };

test('rule planner reproduces the v0.1 sequence', async () => {
  const log: StepId[] = [];
  const run = fakeRun();
  await executePlan(run, new RulePlanner(), fakeRunners(log));
  assert.deepEqual(log.slice(0, 1), ['audit']);
  assert.deepEqual(new Set(log.slice(1, 3)), new Set(['redesign', 'bench']));
  assert.equal(log[3], 'deck');
  assert.equal(run.bus.events.at(-1)?.kind, 'done');
});

test('a failed redesign skips the deck but the run still finishes', async () => {
  const log: StepId[] = [];
  const run = fakeRun();
  await executePlan(run, new RulePlanner(), fakeRunners(log, { fail: ['redesign'] }));
  assert.ok(!log.includes('deck'));
  assert.equal(run.bus.events.at(-1)?.kind, 'done');
  assert.ok(run.bus.events.some((e) => e.kind === 'warning' && e.from === 'redesign'));
});

test('a failed audit is fatal', async () => {
  const run = fakeRun();
  await assert.rejects(executePlan(run, new RulePlanner(), fakeRunners([], { fail: ['audit'] })));
  assert.ok(run.bus.events.some((e) => e.kind === 'error'));
});

test('llm planner can pick a different valid order', async () => {
  const log: StepId[] = [];
  const planner = new LlmPlanner(scripted([
    '{"action":"run","steps":["audit"],"reason":"Start with the audit."}',
    '{"action":"run","steps":["bench"],"reason":"Team first."}',
    '{"action":"run","steps":["redesign"],"reason":"Now the design."}',
    '```json\n{"action":"run","steps":["deck"],"reason":"Wrap up."}\n```',
    '{"action":"finish","reason":"Done."}',
  ]));
  await executePlan(fakeRun(), planner, fakeRunners(log));
  assert.deepEqual(log, ['audit', 'bench', 'redesign', 'deck']);
});

test('llm planner falls back to rules on invalid, garbage or failing output', async () => {
  const log: StepId[] = [];
  const run = fakeRun();
  const planner = new LlmPlanner(scripted([
    '{"action":"run","steps":["deck"],"reason":"Skip ahead."}', // deck before audit: invalid
    'I think we should audit first!',                            // not JSON
    new Error('rate limited'),                                    // model error
    null, null, null, null, null,
  ]));
  await executePlan(run, planner, fakeRunners(log));
  assert.deepEqual(log[0], 'audit');
  assert.ok(log.includes('deck'), 'run still completes through the rule fallback');
  const sources = run.bus.events.filter((e) => e.kind === 'status').map((e) => (e.detail?.data as { source?: string } | undefined)?.source);
  assert.ok(sources.includes('rules-fallback'));
});

test('llm planner cannot finish early while work remains', () => {
  const s: PlanState = { completed: ['audit'], failed: [], attempts: { audit: 1, redesign: 0, bench: 0, deck: 0 }, stepsTaken: 1, facts: { llmAvailable: true } };
  return new LlmPlanner(async () => '{"action":"finish","reason":"Enough."}').next(s).then((d) => { assert.equal(d.source, 'rules-fallback'); assert.equal(d.action, 'run'); });
});

test('guardrails reject repeats, missing prerequisites and exhausted budgets', () => {
  const base: PlanState = { completed: ['audit', 'redesign', 'bench'], failed: [], attempts: { audit: 1, redesign: 1, bench: 1, deck: 0 }, stepsTaken: 2, facts: { llmAvailable: true } };
  assert.match(validateDecision({ action: 'run', steps: ['bench'] }, base)!, /already done|no attempts/);
  assert.match(validateDecision({ action: 'run', steps: ['redesign'] }, base)!, /no reason/);
  assert.equal(validateDecision({ action: 'run', steps: ['redesign'] }, { ...base, facts: { llmAvailable: true, regressions: ['mobile'] } }), null);
  assert.match(validateDecision({ action: 'run', steps: ['deck'] }, { ...base, completed: ['audit'] })!, /needs/);
  assert.match(validateDecision({ action: 'run', steps: ['deck'] }, { ...base, stepsTaken: 8 })!, /budget/);
});

test('rule planner retries a regressed redesign once, only when a model is available', async () => {
  const state = (llm: boolean, redesignAttempts: number): PlanState => ({ completed: ['audit', 'redesign', 'bench'], failed: [], attempts: { audit: 1, redesign: redesignAttempts, bench: 1, deck: 0 }, stepsTaken: 2, facts: { llmAvailable: llm, regressions: ['mobile'] } });
  const p = new RulePlanner();
  assert.deepEqual((await p.next(state(true, 1))).steps, ['redesign']);
  assert.deepEqual((await p.next(state(false, 1))).steps, ['deck']);
  assert.deepEqual((await p.next(state(true, 2))).steps, ['deck']);
});
