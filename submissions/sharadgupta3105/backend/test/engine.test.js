import { describe, it, expect, beforeEach } from 'vitest';
import { createDb } from '../src/db.js';
import { Shortener } from '../src/engine.js';
import { validateUrl, ValidationError } from '../src/validator.js';

function setup() {
  const db = createDb();
  return { db, shortener: new Shortener(db) };
}

describe('validateUrl', () => {
  it('accepts http and https URLs', () => {
    expect(validateUrl('https://example.com')).toBe('https://example.com/');
    expect(validateUrl('http://example.com/a?b=1')).toBe('http://example.com/a?b=1');
  });

  it('rejects javascript:-style and other schemes', () => {
    for (const bad of [
      'javascript:alert(1)',
      'javascript://x',
      'data:text/html,<script>alert(1)</script>',
      'file:///etc/passwd',
      'vbscript:msgbox(1)',
      'ftp://example.com',
      'mailto:user@example.com',
    ]) {
      expect(() => validateUrl(bad)).toThrow(ValidationError);
    }
  });

  it('rejects malformed and empty input', () => {
    for (const bad of ['', '   ', 'not a url', 'example.com', 'https://', 'http://']) {
      expect(() => validateUrl(bad)).toThrow(ValidationError);
    }
    expect(() => validateUrl('https://exa mple.com')).toThrow(ValidationError);
  });

  it('normalizes equivalent URLs', () => {
    expect(validateUrl('HTTPS://Example.com')).toBe('https://example.com/');
  });
});

describe('shorten', () => {
  let shortener;
  beforeEach(() => {
    shortener = setup().shortener;
  });

  it('returns a 6-character base62 code', () => {
    const { code } = shortener.shorten({ url: 'https://example.com' });
    expect(code).toMatch(/^[0-9A-Za-z]{6}$/);
  });

  it('is idempotent for the same URL (M4)', () => {
    const a = shortener.shorten({ url: 'https://example.com/x' });
    const b = shortener.shorten({ url: 'https://example.com/x' });
    expect(a.code).toBe(b.code);
    expect(b.created).toBe(false);
  });

  it('idempotency skips duplicate insert', () => {
    const s = setup();
    const a = s.shortener.shorten({ url: 'https://example.com/y' });
    const b = s.shortener.shorten({ url: 'https://example.com/y' });
    expect(a.code).toBe(b.code);
    const { n } = s.db.prepare('SELECT COUNT(*) AS n FROM links').get();
    expect(n).toBe(1);
  });

  it('uses distinct codes for different URLs', () => {
    const a = shortener.shorten({ url: 'https://a.example' });
    const b = shortener.shorten({ url: 'https://b.example' });
    expect(a.code).not.toBe(b.code);
  });

  it('honours a custom alias', () => {
    const { code } = shortener.shorten({ url: 'https://example.com', customAlias: 'myalias' });
    expect(code).toBe('myalias');
  });

  it('rejects an invalid or taken custom alias', () => {
    shortener.shorten({ url: 'https://example.com', customAlias: 'taken' });
    expect(() => shortener.shorten({ url: 'https://x.com', customAlias: 'bad alias' })).toThrow(/ALIAS_TAKEN|INVALID_ALIAS/);
    expect(() => shortener.shorten({ url: 'https://x.com', customAlias: 'taken' })).toThrow(/ALIAS_TAKEN/);
  });

  it('a custom alias does not reuse the auto code for that URL', () => {
    const auto = shortener.shorten({ url: 'https://example.com/custom' });
    const custom = shortener.shorten({ url: 'https://example.com/custom', customAlias: 'me' });
    expect(custom.code).toBe('me');
    expect(custom.code).not.toBe(auto.code);
  });
});

describe('resolve', () => {
  it('302 for a known, non-expired code and records a click', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    expect(shortener.resolve(code)).toMatchObject({ status: 302, url: 'https://example.com/' });
  });

  it('404 for an unknown code', () => {
    const { shortener } = setup();
    expect(shortener.resolve('zzzzzz')).toEqual({ status: 404 });
  });

  it('410 for an expired link (M2)', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com', expiresAt: 1 });
    expect(shortener.resolve(code)).toEqual({ status: 410 });
  });

  it('302 for a link that expires in the future', () => {
    const { shortener } = setup();
    const future = Math.floor(Date.now() / 1000) + 3600;
    const { code } = shortener.shorten({ url: 'https://example.com', expiresAt: future });
    expect(shortener.resolve(code).status).toBe(302);
  });
});

describe('stats', () => {
  it('returns 0 clicks before any resolution', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    const stats = shortener.stats(code);
    expect(stats.totalClicks).toBe(0);
    expect(stats.lastAccessedAt).toBeNull();
    expect(stats.clicksPerDay).toEqual({});
  });

  it('tracks total clicks and last-accessed time', () => {
    const { shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    shortener.resolve(code);
    shortener.resolve(code);
    const stats = shortener.stats(code);
    expect(stats.totalClicks).toBe(2);
    expect(stats.lastAccessedAt).not.toBeNull();
  });

  it('groups clicks by day', () => {
    const { db, shortener } = setup();
    const { code } = shortener.shorten({ url: 'https://example.com' });
    const link = db.prepare('SELECT id FROM links WHERE code = ?').get(code);
    db.prepare('INSERT INTO clicks (link_id, clicked_at) VALUES (?, ?)').run(link.id, 1000); // 1970-01-01
    db.prepare('INSERT INTO clicks (link_id, clicked_at) VALUES (?, ?)').run(link.id, 1001);
    const stats = shortener.stats(code);
    expect(stats.totalClicks).toBe(2);
    expect(stats.clicksPerDay['1970-01-01']).toBe(2);
  });

  it('returns null for an unknown code', () => {
    const { shortener } = setup();
    expect(shortener.stats('nope')).toBeNull();
  });
});
