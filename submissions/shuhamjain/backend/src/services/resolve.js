'use strict';

/**
 * Resolve a code to its redirect target.
 * Returns { status, location } or { status: 404 } / { status: 410 }.
 */
function resolve(db, code, now = Date.now()) {
  const row = db.prepare('SELECT * FROM links WHERE code = ?').get(code);

  if (!row) {
    return { status: 404 };
  }
  if (row.expires_at !== null && row.expires_at <= now) {
    return { status: 410 };
  }
  return { status: 302, location: row.url, linkId: row.id };
}

/**
 * Record a click for a successful resolve. Upserts the (link_id, day) row and
 * bumps last_accessed_at. Uses UTC for the day bucket so stats are consistent
 * regardless of server timezone.
 */
function recordClick(db, linkId, now = Date.now()) {
  const day = new Date(now).toISOString().slice(0, 10);
  db.prepare(
    `INSERT INTO clicks (link_id, day, count) VALUES (?, ?, 1)
     ON CONFLICT (link_id, day) DO UPDATE SET count = count + 1`
  ).run(linkId, day);
  db.prepare('UPDATE links SET last_accessed_at = ? WHERE id = ?').run(now, linkId);
}

module.exports = { resolve, recordClick };