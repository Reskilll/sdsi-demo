// Core shortening engine — pure logic, no HTTP concerns. The Express layer
// (app.js) is a thin interface over this class, keeping the two separable.

import { randomInt } from 'node:crypto';
import { validateUrl, ValidationError } from './validator.js';

const BASE62 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
const CODE_LENGTH = 6; // within the required 6–8 character range
const COLLISION_RETRIES = 5;
const ALIAS_RE = /^[A-Za-z0-9_-]{1,64}$/;

const nowSeconds = () => Math.floor(Date.now() / 1000);
const iso = (seconds) => (seconds == null ? null : new Date(seconds * 1000).toISOString());

function randomCode(length) {
  let out = '';
  for (let i = 0; i < length; i += 1) out += BASE62[randomInt(62)];
  return out;
}

// Accepts an ISO 8601 string or unix seconds. A past date is allowed so an
// already-expired link can be created (and resolves to 410) deterministically.
function normalizeExpiry(value) {
  let tsMs;
  if (value instanceof Date) {
    tsMs = value.getTime();
  } else if (typeof value === 'number' && Number.isFinite(value)) {
    tsMs = value * 1000; // unix seconds
  } else if (typeof value === 'string') {
    tsMs = Date.parse(value);
    if (Number.isNaN(tsMs)) {
      throw new ValidationError('INVALID_EXPIRY', 'Expiry must be an ISO 8601 date or unix seconds.');
    }
  } else {
    throw new ValidationError('INVALID_EXPIRY', 'Expiry must be an ISO 8601 date or unix seconds.');
  }
  return Math.floor(tsMs / 1000);
}

export class Shortener {
  constructor(db) {
    this.db = db;
  }

  shorten({ url, customAlias = null, expiresAt = null } = {}) {
    const normalized = validateUrl(url);

    const alias = customAlias == null || customAlias === '' ? null : customAlias;
    if (alias !== null && (typeof alias !== 'string' || !ALIAS_RE.test(alias))) {
      throw new ValidationError('INVALID_ALIAS', 'Alias must be 1–64 characters of A–Z, a–z, 0–9, "_" or "-".');
    }

    const expires = expiresAt == null ? null : normalizeExpiry(expiresAt);

    // M4: without a custom alias, shortening the same URL is idempotent.
    if (alias === null) {
      const existing = this.db
        .prepare('SELECT code, expires_at FROM links WHERE url = ? AND is_custom = 0')
        .get(normalized);
      if (existing) {
        return {
          code: existing.code,
          url: normalized,
          expiresAt: iso(existing.expires_at),
          created: false,
        };
      }
    }

    let code;
    if (alias !== null) {
      if (this.db.prepare('SELECT 1 FROM links WHERE code = ?').get(alias)) {
        throw new ValidationError('ALIAS_TAKEN', `Alias "${alias}" is already in use.`);
      }
      code = alias;
    } else {
      code = this._uniqueCode();
    }

    this.db
      .prepare('INSERT INTO links (code, url, is_custom, created_at, expires_at) VALUES (?, ?, ?, ?, ?)')
      .run(code, normalized, alias !== null ? 1 : 0, nowSeconds(), expires);

    return { code, url: normalized, expiresAt: iso(expires), created: true };
  }

  _uniqueCode() {
    for (let i = 0; i < COLLISION_RETRIES; i += 1) {
      const code = randomCode(CODE_LENGTH);
      if (!this.db.prepare('SELECT 1 FROM links WHERE code = ?').get(code)) return code;
    }
    throw new Error('Could not allocate a unique code; please retry.');
  }

  resolve(code) {
    if (typeof code !== 'string' || code.length === 0) return { status: 404 };
    const link = this.db
      .prepare('SELECT id, url, expires_at FROM links WHERE code = ?')
      .get(code);
    if (!link) return { status: 404 };
    if (link.expires_at !== null && link.expires_at <= nowSeconds()) return { status: 410 };

    this.db.prepare('INSERT INTO clicks (link_id, clicked_at) VALUES (?, ?)').run(link.id, nowSeconds());
    return { status: 302, url: link.url };
  }

  stats(code) {
    const link = this.db
      .prepare('SELECT id, code, url, created_at, expires_at FROM links WHERE code = ?')
      .get(code);
    if (!link) return null;

    const { n: totalClicks } = this.db
      .prepare('SELECT COUNT(*) AS n FROM clicks WHERE link_id = ?')
      .get(link.id);
    const { t: last } = this.db
      .prepare('SELECT MAX(clicked_at) AS t FROM clicks WHERE link_id = ?')
      .get(link.id);
    const perDay = this.db
      .prepare(
        "SELECT date(clicked_at, 'unixepoch') AS day, COUNT(*) AS clicks " +
          'FROM clicks WHERE link_id = ? GROUP BY day ORDER BY day',
      )
      .all(link.id);

    return {
      code: link.code,
      url: link.url,
      createdAt: iso(link.created_at),
      expiresAt: iso(link.expires_at),
      totalClicks,
      lastAccessedAt: last == null ? null : iso(last),
      clicksPerDay: Object.fromEntries(perDay.map((r) => [r.day, r.clicks])),
    };
  }
}
