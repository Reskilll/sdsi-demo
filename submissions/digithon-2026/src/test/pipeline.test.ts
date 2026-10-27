import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const api = runInNewContext(`${readFileSync('web/pipeline.js', 'utf8')}\n({ PIPE_COMPANIES, PIPE_TENDERS, PIPE_STAGES, PIPE_TOTAL_SECS, pipeStagesFor, pipeStageIndex, pipeProgress, pipeRandom, pipeBrand })`) as {
  PIPE_COMPANIES: { name: string; sector: string; domain: string }[]; PIPE_STAGES: { agent: string; secs: number }[]; PIPE_TOTAL_SECS: number;
  PIPE_TENDERS: { name: string; tender: { fit: boolean; why: string } }[]; pipeStagesFor: (i: object) => { key: string; agent: string; secs: number }[];
  pipeStageIndex: (s: number, st?: object[]) => number; pipeProgress: (s: number, st?: object[]) => number; pipeRandom: (seed: number) => () => number; pipeBrand: (t: string, u: string) => string;
};

test('there are 50 distinct Indian company names, each with a sector and a website', () => {
  assert.equal(api.PIPE_COMPANIES.length, 50);
  assert.equal(new Set(api.PIPE_COMPANIES.map((c) => c.name)).size, 50);
  assert.equal(new Set(api.PIPE_COMPANIES.map((c) => c.domain)).size, 50);
  for (const c of api.PIPE_COMPANIES) { assert.ok(c.sector); assert.match(c.domain, /^[a-z0-9-]+(\.[a-z0-9-]+)+$/); }
  for (const real of ['HDFC Bank', 'Samsung India', 'Allbirds', 'Samsung UK']) assert.ok(!api.PIPE_COMPANIES.some((c) => c.name === real), `${real} is a real report and must not also be a simulated entry`);
  const sectors = new Set(api.PIPE_COMPANIES.map((c) => c.sector));
  for (const s of ['Banking', 'E-commerce', 'Healthcare', 'Infrastructure', 'Manufacturing', 'FMCG']) assert.ok(sectors.has(s), `no ${s} companies`);
});

test('a website moves through the agents in order and then finishes', () => {
  assert.equal(api.pipeStageIndex(0), 0);
  let last = -1; for (let s = 0; s <= api.PIPE_TOTAL_SECS; s += 0.5) { const i = api.pipeStageIndex(s); assert.ok(i >= last, 'never goes backwards'); last = i; }
  assert.equal(api.pipeStageIndex(api.PIPE_TOTAL_SECS), api.PIPE_STAGES.length, 'finished');
  assert.equal(api.pipeProgress(-5), 0); assert.equal(api.pipeProgress(api.PIPE_TOTAL_SECS * 3), 1);
});

test('the seeded sample history is the same every time', () => {
  const a = api.pipeRandom(7), b = api.pipeRandom(7);
  assert.deepEqual([a(), a(), a()], [b(), b(), b()]);
});

test('report titles become company names', () => {
  assert.equal(api.pipeBrand('Samsung India | Mobile | Tablets | TV', 'https://www.samsung.com/in/'), 'Samsung India');
  assert.equal(api.pipeBrand('Personal Banking & Netbanking Services | HDFC Bank', 'https://www.hdfc.bank.in/'), 'HDFC Bank');
});

test('the Market Researcher is the first agent to work on a website', () => {
  assert.equal(api.PIPE_STAGES[1].agent, 'research');
});

test('a government tender is triaged first; only a relevant one goes on to the agents', () => {
  const fit = api.PIPE_TENDERS.find((t) => t.tender.fit)!, skip = api.PIPE_TENDERS.find((t) => !t.tender.fit)!;
  const a = api.pipeStagesFor(fit), b = api.pipeStagesFor(skip);
  assert.equal(a[0].agent, 'tenders'); assert.equal(b[0].agent, 'tenders');
  assert.equal(b.length, 1, 'a tender that is not relevant stops at triage');
  assert.ok(a.some((s) => s.agent === 'deck'), 'a relevant tender gets a deck');
  assert.equal(api.pipeStageIndex(a[0].secs + 0.1, a), 1);
  assert.equal(api.pipeProgress(1e6, b), 1);
  for (const t of api.PIPE_TENDERS) assert.ok(t.tender.why);
});
