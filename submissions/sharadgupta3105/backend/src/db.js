// SQLite storage layer. Zero-dependency: uses Node's built-in `node:sqlite`
// (Node >= 22.5). Embedded, zero-config, and safe by default:
//   * WAL journal mode for safe concurrent readers
//   * foreign keys ON (cascading click cleanup)
//   * a partial unique index enforces idempotency for non-custom links
//
// All statements are prepared (parameterized), so user input is never
// interpolated into SQL.

import { DatabaseSync } from 'node:sqlite';

export function createDb(path = ':memory:') {
  const db = new DatabaseSync(path);
  db.exec('PRAGMA journal_mode = WAL');
  db.exec('PRAGMA foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS links (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      code       TEXT    NOT NULL UNIQUE,
      url        TEXT    NOT NULL,
      is_custom  INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL,
      expires_at INTEGER
    );

    -- Same URL (no custom alias) always maps to the same code.
    CREATE UNIQUE INDEX IF NOT EXISTS idx_links_noncustom_url
      ON links(url) WHERE is_custom = 0;

    CREATE TABLE IF NOT EXISTS clicks (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      link_id    INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
      clicked_at INTEGER NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_clicks_link ON clicks(link_id, clicked_at);
  `);

  return db;
}
