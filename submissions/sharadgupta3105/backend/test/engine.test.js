import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createDb } from '../src/db.js';
import { Shortener } from '../src/engine.js';
import { validateUrl, ValidationError } from '../src/validator.js';

function setup() {
  const db = createDb();
  return { db, shortener: new Shortener(db) };
}

describe('validateUrl', () => {
  it('accepts http and https URLs', () => {
    assert.equal(validateUrl('https://example.com'), 'https://example.com/');
    assert.equal(validateUrl('http://example.com/a?b=1'), 'http://example.com/a?b=1');
  });

  it('rejects javascript:-style and other schemes', () => {
    const bad = [
      'javascript:alert(1)',
      'javascript://x',
      'data:text/html,<script>alert(1)</script>',
      'file:///etc/passwd',
      'vbscript:msgbox(1)',
      'ftp://example.com',
      'mailto:user@example.com',
    ];
    for (const u of bad) {
      assert.throws(() => validateUrl(u), ValidationError);
    }
  });

  it('rejects malformed and empty input', () => {
    const bad = ['', '   ', 'not a url', 'example.com', 'https://', 'http://'];
    for (const u of bad) {
      assert.throws(() => validateUrl(u), ValidationError);
    }
    assert.throws(() => validateUrl('https://exa mple.com'), ValidationError);
  });

  it('normalizes equivalent URLs', () => {
    assert.equal(validateUrl('HTTPS://Example.com'), 'https://example.com/');
  });
});

describe('shorten', () => {
  let shortener;
  beforeEach(() => {
    shortener = setup().shortener;
  });

  it('returns a 6-character base62 code', () => {
    const { code } = shortener.shorten({ url: 'https://example.com' });
    assert.match(code, /^[0-9A-Za-z]{6}$/);
  });

  it('is idempotent for the same URL (M4)', () => {
    const a = shortener.shorten({ url: 'https://example.com/x' });
    const b = shortener.shorten({ url: 'https://example.com/x' });
    assert.equal(a.code, b.code);
    assert.equal(b.created, false);
  });

  it('idempotency skips duplicate insert', () => {
    const s = setup();
    const a = s.shortener.shorten({ url: 'https://example.com/y' });
    const b = s.shortener.shorten({ url: 'https://example.com/y' });
    assert.equal(a.code, b.code);
    const { n } = s.db.prepare('SELECT COUNT(*) AS n FROM links').get();
    assert.equal(n, 1);
  });

  it('uses distinct codes for different URLs', () => {
    const a = shortener.shorten({ url: 'https://a.example' });
    const b = shortener.shorten({ url: 'https://b.example' });
    assert.notEqual(a.code, b.code);
  });

  it('honours a custom alias', () => {
    const { code } = shortener.shorten({ url: 'https://example.com', customAlias: 'myalias' });
    assert.equal(code, 'myalias');
  });

  it('rejects an invalid or taken custom alias', () => {
    shortener.shorten({ url: 'https://example.com', customAlias: 'taken' });
    assert.throws(
      () => shortener.shorten({ url: 'https://x.com', customAlias: 'bad alias' }),
      (err) => err instanceof ValidationError && err.code === 'INVALID_ALIAS',
    );
    assert.throws(
      () => shortener.shorten({ url: 'https://x.com', customAlias: 'taken' }),
      (err) => err instanceof ValidationError && err.code === 'ALIAS_TAKEN',
    );
  });

  it('a custom alias does not reuse the auto code for that URL', () => {
    const auto = shortener.shorten({ url: 'https://example.com/custom' });
    const custom = shortener.shorten({ url: 'https://example.com/custom', customAlias: 'me' });
    assert.equal(custom.code, 'me');
    assert.notEqual(custom.code, auto.code);
  });
});

describe('resolve', () => {
  it('302 for a known, non-expired code and records a click', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    assert.deepEqual(shortener.resolve(code), { status: 302, url: 'https://example.com/' });
  });

  it('404 for an unknown code', () => {
    const { shortener } = setup();
    assert.deepEqual(shortener.resolve('zzzzzz'), { status: 404 });
  });

  it('410 for an expired link (M2)', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com', expiresAt: 1 });
    assert.deepEqual(shortener.resolve(code), { status: 410 });
  });

  it('302 for a link that expires in the future', () => {
    const { shortener } = setup();
    const future = Math.floor(Date.now() / 1000) + 3600;
    const { code } = shortener.shorten({ url: 'https://example.com', expiresAt: future });
    assert.equal(shortener.resolve(code).status, 302);
  });
});

describe('stats', () => {
  it('returns 0 clicks before any resolution', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    const stats = shortener.stats(code);
    assert.equal(stats.totalClicks, 0);
    assert.equal(stats.lastAccessedAt, null);
    assert.deepEqual(stats.clicksPerDay, {});
  });

  it('tracks total clicks and last-accessed time', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    shortener.resolve(code);
    shortener.resolve(code);
    const stats = shortener.stats(code);
    assert.equal(stats.totalClicks, 2);
    assert.notEqual(stats.lastAccessedAt, null);
  });

  it('groups clicks by day', () => {
    const { db, shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    const link = db.prepare('SELECT id FROM links WHERE code = ?').get(code);
    db.prepare('INSERT INTO clicks (link_id, clicked_at) VALUES (?, ?)').run(link.id, 1000); // 1970-01-01
    db.prepare('INSERT INTO clicks (link_id, clicked_at) VALUES (?, ?)').run(link.id, 1001);
    const stats = shortener.stats(code);
    assert.equal(stats.totalClicks, 2);
    assert.equal(stats.clicksPerDay['1970-01-01'], 2);
  });

  it('returns null for an unknown code', () => {
    const { shortener } = setup();
    assert.equal(shortener.stats('nope'), null);
  });
});
