'use strict';

function stats(db, code) {
  const link = db.prepare('SELECT * FROM links WHERE code = ?').get(code);
  if (!link) {
    return null;
  }

  const clicks = db
    .prepare('SELECT day, count FROM clicks WHERE link_id = ? ORDER BY day ASC')
    .all(link.id);

  const totalClicks = clicks.reduce((sum, c) => sum + c.count, 0);

  return {
    code: link.code,
    originalUrl: link.url,
    custom: link.custom === 1,
    createdAt: link.created_at,
    expiresAt: link.expires_at,
    lastAccessedAt: link.last_accessed_at,
    totalClicks,
    clicksPerDay: clicks.map((c) => ({ day: c.day, count: c.count })),
  };
}

module.exports = { stats };