'use strict';

const { encode } = require('../lib/base62');
const { canonicalize, hashUrl } = require('../lib/url');
const { ValidationError, ConflictError } = require('../lib/errors');

const ALIAS_RE = /^[A-Za-z0-9_-]{1,32}$/;
const RESERVED = new Set([
  'api', 'stats', 'healthz', 'health', 'shorten', 'resolve', 'favicon.ico', 'robots.txt',
]);

function shorten(db, input) {
  const { url, ttl, alias } = input;

  const { canonical, hostname } = canonicalize(url);
  const urlHash = hashUrl(canonical);

  // --- custom alias path (M4: alias always creates its own mapping) ---
  if (alias !== undefined && alias !== null) {
    validateAlias(alias);
    const expiresAt = ttl === undefined ? null : normalizeTtl(ttl);
    const now = Date.now();
    try {
      const info = db
        .prepare('INSERT INTO links (url, url_hash, code, custom, expires_at, created_at) VALUES (?, ?, ?, 1, ?, ?)')
        .run(canonical, urlHash, alias, expiresAt, now);
      return buildResult({ id: info.lastInsertRowid, url: canonical, code: alias, custom: 1, expiresAt, createdAt: now });
    } catch (err) {
      if (isUniqueViolation(err)) {
        throw new ConflictError(`alias "${alias}" is already in use`);
      }
      throw err;
    }
  }

  // --- auto code path (M4: idempotent on canonical URL) ---
  const existing = db
    .prepare('SELECT * FROM links WHERE url_hash = ? AND custom = 0')
    .get(urlHash);
  if (existing) {
    return buildResult(existing);
  }

  const expiresAt = ttl === undefined ? null : normalizeTtl(ttl);

  // node:sqlite has no .transaction() helper; wrap in an explicit transaction.
  db.exec('BEGIN');
  try {
    const again = db
      .prepare('SELECT * FROM links WHERE url_hash = ? AND custom = 0')
      .get(urlHash);
    if (again) {
      db.exec('COMMIT');
      return buildResult(again);
    }
    const counter = db.prepare('SELECT value FROM counter WHERE id = 1').get();
    const code = encode(counter.value);
    db.prepare('UPDATE counter SET value = value + 1 WHERE id = 1').run();
    const now = Date.now();
    const info = db
      .prepare('INSERT INTO links (url, url_hash, code, custom, expires_at, created_at) VALUES (?, ?, ?, 0, ?, ?)')
      .run(canonical, urlHash, code, expiresAt, now);
    db.exec('COMMIT');
    return buildResult(db.prepare('SELECT * FROM links WHERE id = ?').get(info.lastInsertRowid));
  } catch (err) {
    db.exec('ROLLBACK');
    throw err;
  }
}

function validateAlias(alias) {
  if (typeof alias !== 'string' || !ALIAS_RE.test(alias)) {
    throw new ValidationError('alias must be 1-32 characters of letters, digits, "_" or "-"');
  }
  if (RESERVED.has(alias.toLowerCase())) {
    throw new ValidationError(`alias "${alias}" is reserved`);
  }
}

// TTL in seconds; 0 seconds = valid (expire immediately). Negative/invalid -> 422->400.
function normalizeTtl(ttl) {
  const n = Number(ttl);
  if (!Number.isFinite(n) || n < 0) {
    throw new ValidationError('ttl must be a non-negative number of seconds');
  }
  if (n > 60 * 60 * 24 * 365 * 10) {
    throw new ValidationError('ttl is too large');
  }
  return Date.now() + Math.floor(n * 1000);
}

function isUniqueViolation(err) {
  return err && /UNIQUE constraint failed/i.test(String(err.message));
}

function buildResult(row) {
  return {
    code: row.code,
    shortUrl: `/${row.code}`,
    originalUrl: row.url,
    custom: row.custom === 1,
    expiresAt: row.expires_at,
    createdAt: row.created_at,
  };
}

module.exports = { shorten, ALIAS_RE, RESERVED };