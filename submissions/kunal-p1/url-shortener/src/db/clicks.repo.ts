/** `clicks` table data access and aggregation. */

import type { Database as DatabaseType } from 'better-sqlite3';

import type { ClickRow, NewClick } from '../domain/types.js';

export interface ClickTotals {
  total: number;
  uniqueVisitors: number;
  first: number | null;
  last: number | null;
}

export interface DayBucket {
  day: string;
  clicks: number;
}

export class ClicksRepository {
  readonly #db: DatabaseType;
  readonly #insert;
  readonly #totals;
  readonly #perDay;
  readonly #recent;

  constructor(db: DatabaseType) {
    this.#db = db;
    this.#insert = db.prepare(`
      INSERT INTO clicks (code, clicked_at, ip_hash, user_agent, referer)
      VALUES (@code, @clickedAt, @ipHash, @userAgent, @referer)
    `);
    this.#totals = db.prepare(`
      SELECT COUNT(*)                     AS total,
             COUNT(DISTINCT ip_hash)      AS uniqueVisitors,
             MIN(clicked_at)              AS first,
             MAX(clicked_at)              AS last
        FROM clicks
       WHERE code = ?
    `);
    // strftime('%Y-%m-%d', ..., 'unixepoch') keeps bucketing in UTC and lets
    // SQLite use the (code, clicked_at) index for the range scan.
    this.#perDay = db.prepare(`
      SELECT strftime('%Y-%m-%d', clicked_at / 1000, 'unixepoch') AS day,
             COUNT(*) AS clicks
        FROM clicks
       WHERE code = ?
       GROUP BY day
       ORDER BY day ASC
    `);
    this.#recent = db.prepare(`
      SELECT * FROM clicks WHERE code = ? ORDER BY clicked_at DESC, id DESC LIMIT ?
    `);
  }

  insert(click: NewClick): void {
    this.#insert.run(click);
  }

  totals(code: string): ClickTotals {
    const row = this.#totals.get(code) as
      | { total: number; uniqueVisitors: number; first: number | null; last: number | null }
      | undefined;
    return {
      total: row?.total ?? 0,
      uniqueVisitors: row?.uniqueVisitors ?? 0,
      first: row?.first ?? null,
      last: row?.last ?? null,
    };
  }

  perDay(code: string): DayBucket[] {
    return this.#perDay.all(code) as DayBucket[];
  }

  recent(code: string, limit = 20): ClickRow[] {
    return this.#recent.all(code, limit) as ClickRow[];
  }

  countAll(): number {
    const row = this.#db.prepare('SELECT COUNT(*) AS total FROM clicks').get() as
      | { total: number }
      | undefined;
    return row?.total ?? 0;
  }
}
