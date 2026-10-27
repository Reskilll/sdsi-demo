/**
 * SQLite connection factory.
 *
 * Pragmas are the important part of this file:
 * - `journal_mode = WAL` lets readers and the writer coexist (stats reads
 *   during redirect writes instead of blocking).
 * - `synchronous = NORMAL` is the standard durability/throughput trade-off for
 *   WAL mode: safe against application crashes, small window on power loss.
 * - `busy_timeout = 5000` makes concurrent writers wait instead of throwing
 *   SQLITE_BUSY.
 * - `foreign_keys = ON` enforces the clicks -> links relationship.
 */

import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

import Database from 'better-sqlite3';
import type { Database as DatabaseType } from 'better-sqlite3';

import { runMigrations } from './migrations.js';

export interface OpenDatabaseOptions {
  /** File path, or `:memory:` for an ephemeral database. */
  path: string;
  /** Log SQL emitted by better-sqlite3 (development only). */
  verbose?: boolean;
}

export function openDatabase(options: OpenDatabaseOptions): DatabaseType {
  const inMemory = options.path === ':memory:';
  const filename = inMemory ? ':memory:' : resolve(options.path);

  if (!inMemory) {
    mkdirSync(dirname(filename), { recursive: true });
  }

  const db = new Database(filename, options.verbose ? { verbose: console.warn } : {});

  // WAL is not supported for in-memory databases.
  if (!inMemory) {
    db.pragma('journal_mode = WAL');
    // FULL gives maximum durability but slower writes; NORMAL is the standard WAL pairing.
    db.pragma('synchronous = NORMAL');
  }
  db.pragma('busy_timeout = 5000');
  db.pragma('foreign_keys = ON');
  db.pragma('temp_store = MEMORY');

  runMigrations(db);
  return db;
}

export type { DatabaseType };
