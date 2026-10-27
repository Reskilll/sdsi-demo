'use strict';

const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');
const { MIN_VALUE } = require('./lib/base62');

function openDb(dbPath) {
  const resolved = dbPath || path.join(__dirname, '..', 'data', 'shortener.db');
  if (resolved !== ':memory:') {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
  }

  const db = new Database(resolved);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  migrate(db);
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS links (
      id               INTEGER PRIMARY KEY AUTOINCREMENT,
      url              TEXT    NOT NULL,
      url_hash         TEXT    NOT NULL,
      code             TEXT    NOT NULL UNIQUE,
      custom           INTEGER NOT NULL DEFAULT 0,
      expires_at       INTEGER,
      created_at       INTEGER NOT NULL,
      last_accessed_at INTEGER
    );

    -- Idempotency lookup: one auto code per canonical URL.
    CREATE INDEX IF NOT EXISTS idx_links_hash_custom ON links (url_hash, custom);
    -- Optional janitor / expiry scans.
    CREATE INDEX IF NOT EXISTS idx_links_expires ON links (expires_at);

    CREATE TABLE IF NOT EXISTS clicks (
      link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
      day     TEXT    NOT NULL,          -- 'YYYY-MM-DD' (UTC)
      count   INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (link_id, day)
    );

    CREATE TABLE IF NOT EXISTS counter (
      id    INTEGER PRIMARY KEY CHECK (id = 1),
      value INTEGER NOT NULL
    );
  `);

  db.prepare('INSERT OR IGNORE INTO counter (id, value) VALUES (1, ?)').run(MIN_VALUE);
}

module.exports = { openDb };