'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { build } = require('../src/server');
const { openDb } = require('../src/db');

async function makeApp() {
  const db = openDb(':memory:');
  const app = await build({ db, logger: false });
  return { app, db };
}

test('M1 + M2: shorten then resolve redirects with 302 and correct Location', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  const shortenRes = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/hello' },
  });
  assert.strictEqual(shortenRes.statusCode, 200);
  const { code, shortUrl } = shortenRes.json();
  assert.match(code, /^[0-9A-Za-z]{6,8}$/);
  assert.ok(shortUrl.endsWith(`/${code}`), `shortUrl should end with /${code}`);

  const r = await app.inject({ method: 'GET', url: `/${code}` });
  assert.strictEqual(r.statusCode, 302);
  assert.strictEqual(r.headers.location, 'https://example.com/hello');
});

test('M3: invalid URLs and bad schemes return 400', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  for (const url of ['javascript:alert(1)', 'ftp://example.com', 'not a url', '']) {
    const res = await app.inject({ method: 'POST', url: '/api/shorten', payload: { url } });
    assert.strictEqual(res.statusCode, 400, `expected 400 for ${url}`);
  }
});

test('M4: same URL twice returns the same code; custom alias creates separate mapping', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  const payload = { url: 'https://example.com/same' };
  const first = await app.inject({ method: 'POST', url: '/api/shorten', payload });
  const second = await app.inject({ method: 'POST', url: '/api/shorten', payload });
  assert.strictEqual(first.statusCode, 200);
  assert.strictEqual(first.json().code, second.json().code, 'auto-shorten must be idempotent');

  const aliased = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/same', alias: 'myalias' },
  });
  assert.strictEqual(aliased.statusCode, 200);
  assert.strictEqual(aliased.json().code, 'myalias');
  assert.notStrictEqual(aliased.json().code, first.json().code);

  // Alias collision -> 409.
  const clash = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/other', alias: 'myalias' },
  });
  assert.strictEqual(clash.statusCode, 409);
});

test('M2: unknown code -> 404, expired code -> 410', async (t) => {
  const { app, db } = await makeApp();
  t.after(() => app.close());

  const unknown = await app.inject({ method: 'GET', url: '/doesnotexist' });
  assert.strictEqual(unknown.statusCode, 404);

  const res = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/expires', ttl: 0 }, // expire immediately
  });
  const { code } = res.json();
  const gone = await app.inject({ method: 'GET', url: `/${code}` });
  assert.strictEqual(gone.statusCode, 410);
});

test('M5: stats track total, per-day counts, and last accessed time', async (t) => {
  const { app, db } = await makeApp();
  t.after(() => app.close());

  const res = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/tracked' },
  });
  const { code } = res.json();

  await app.inject({ method: 'GET', url: `/${code}` });
  await app.inject({ method: 'GET', url: `/${code}` });

  const statsRes = await app.inject({ method: 'GET', url: `/api/stats/${code}` });
  assert.strictEqual(statsRes.statusCode, 200);
  const s = statsRes.json();
  assert.strictEqual(s.totalClicks, 2);
  assert.strictEqual(s.clicksPerDay.length, 1);
  assert.strictEqual(s.clicksPerDay[0].count, 2);
  assert.ok(s.lastAccessedAt > 0);

  // Stats for unknown code -> 404.
  const missing = await app.inject({ method: 'GET', url: '/api/stats/nope' });
  assert.strictEqual(missing.statusCode, 404);
});

test('healthz responds ok', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());
  const res = await app.inject({ method: 'GET', url: '/healthz' });
  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(res.json(), { ok: true });
});

test('edge: aliases are validated (regex + reserved words)', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  for (const alias of ['stats', 'api', 'healthz']) {
    const res = await app.inject({
      method: 'POST',
      url: '/api/shorten',
      payload: { url: 'https://example.com/x', alias },
    });
    assert.strictEqual(res.statusCode, 400, `reserved alias "${alias}" should be 400`);
  }

  const bad = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/y', alias: 'has space and !' },
  });
  assert.strictEqual(bad.statusCode, 400);
});

test('edge: invalid ttl rejected', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  for (const ttl of [-1, -5]) {
    const res = await app.inject({
      method: 'POST',
      url: '/api/shorten',
      payload: { url: 'https://example.com/x', ttl },
    });
    assert.strictEqual(res.statusCode, 400, `ttl=${ttl} should be 400`);
  }

  // Non-numeric string should also be rejected.
  const strRes = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'https://example.com/y', ttl: 'abc' },
  });
  assert.strictEqual(strRes.statusCode, 400);
});

test('edge: cannot shorten a URL pointing back at this service', async (t) => {
  const { app } = await makeApp();
  t.after(() => app.close());

  const res = await app.inject({
    method: 'POST',
    url: '/api/shorten',
    payload: { url: 'http://localhost/foo' },
  });
  assert.strictEqual(res.statusCode, 400);
});