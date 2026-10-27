/**
 * `links` table data access.
 *
 * Prepared statements are created once per repository instance: better-sqlite3
 * statements are synchronous and compiled, which is what keeps the redirect
 * path in the low-hundreds-of-microseconds range.
 */

import type { Database as DatabaseType } from 'better-sqlite3';

import type { LinkRow } from '../domain/types.js';

export interface InsertLinkParams {
  code: string;
  url: string;
  urlHash: string;
  alias: boolean;
  createdAt: number;
  expiresAt: number | null;
}

export class LinksRepository {
  readonly #db: DatabaseType;
  readonly #insert;
  readonly #findByCode;
  readonly #findLiveByHash;
  readonly #findAnyByHash;
  readonly #findByAliasUrl;
  readonly #incrementClicks;
  readonly #softDelete;
  readonly #listAll;
  readonly #countAll;
  readonly #countLinks;
  readonly #purgeExpired;

  constructor(db: DatabaseType) {
    this.#db = db;
    this.#insert = db.prepare(`
      INSERT INTO links (code, url, url_hash, alias, created_at, expires_at)
      VALUES (@code, @url, @urlHash, @alias, @createdAt, @expiresAt)
    `);
    this.#findByCode = db.prepare(`
      SELECT * FROM links WHERE code = ? COLLATE BINARY AND deleted_at IS NULL
    `);
    this.#findLiveByHash = db.prepare(`
      SELECT * FROM links
      WHERE url_hash = ? AND alias = 0 AND deleted_at IS NULL
        AND (expires_at IS NULL OR expires_at > ?)
      ORDER BY created_at ASC, id ASC
      LIMIT 1
    `);
    this.#findAnyByHash = db.prepare(`
      SELECT * FROM links WHERE url_hash = ? AND alias = 0 ORDER BY created_at ASC, id ASC LIMIT 1
    `);
    this.#findByAliasUrl = db.prepare(`
      SELECT * FROM links WHERE code = ? AND url_hash = ? AND deleted_at IS NULL LIMIT 1
    `);
    this.#incrementClicks = db.prepare(`
      UPDATE links
         SET click_count = click_count + 1,
             last_accessed_at = @clickedAt
       WHERE code = @code
    `);
    this.#softDelete = db.prepare(`
      UPDATE links SET deleted_at = @deletedAt
       WHERE code = @code AND deleted_at IS NULL
    `);
    this.#listAll = db.prepare(`
      SELECT * FROM links
       WHERE deleted_at IS NULL
       ORDER BY created_at DESC, id DESC
       LIMIT @limit OFFSET @offset
    `);
    this.#countAll = db.prepare(`SELECT COUNT(*) AS total FROM links WHERE deleted_at IS NULL`);
    this.#countLinks = db.prepare(`SELECT COUNT(*) AS total FROM links WHERE deleted_at IS NULL`);
    this.#purgeExpired = db.prepare(`
      DELETE FROM links
       WHERE expires_at IS NOT NULL AND expires_at < @before
    `);
  }

  insert(params: InsertLinkParams): LinkRow {
    this.#insert.run({ ...params, alias: params.alias ? 1 : 0 });
    const row = this.findByCodeIncludingDeleted(params.code);
    if (!row) {
      throw new Error(`Inserted link ${params.code} could not be read back`);
    }
    return row;
  }

  /** Case-sensitive lookup by code; deleted links are excluded. */
  findByCode(code: string): LinkRow | undefined {
    return this.#findByCode.get(code) as LinkRow | undefined;
  }

  /** Includes soft-deleted rows; used only right after insert. */
  findByCodeIncludingDeleted(code: string): LinkRow | undefined {
    return this.#db
      .prepare('SELECT * FROM links WHERE code = ? COLLATE BINARY')
      .get(code) as LinkRow | undefined;
  }

  /** Live (not deleted, not expired) non-alias link for a URL hash. */
  findLiveByHash(urlHash: string, now: number): LinkRow | undefined {
    return this.#findLiveByHash.get(urlHash, now) as LinkRow | undefined;
  }

  /** Any non-alias link for a URL hash, including expired/deleted ones. */
  findAnyByHash(urlHash: string): LinkRow | undefined {
    return this.#findAnyByHash.get(urlHash) as LinkRow | undefined;
  }

  findByAliasAndUrl(code: string, urlHash: string): LinkRow | undefined {
    return this.#findByAliasUrl.get(code, urlHash) as LinkRow | undefined;
  }

  incrementClicks(code: string, clickedAt: number): void {
    this.#incrementClicks.run({ code, clickedAt });
  }

  softDelete(code: string, deletedAt: number): number {
    return this.#softDelete.run({ code, deletedAt }).changes;
  }

  list(limit: number, offset: number): LinkRow[] {
    return this.#listAll.all({ limit, offset }) as LinkRow[];
  }

  count(): number {
    const row = this.#countAll.get() as { total: number } | undefined;
    return row?.total ?? 0;
  }

  /** Maintained for future statistics endpoints (all links, including deleted). */
  countAll(): number {
    const row = this.#countLinks.get() as { total: number } | undefined;
    return row?.total ?? 0;
  }

  /** Physically delete links that expired before `before`; returns rows removed. */
  purgeExpiredBefore(before: number): number {
    return this.#purgeExpired.run({ before }).changes;
  }

  /** True when the code exists in any state (used for alias collision checks). */
  codeExists(code: string): boolean {
    const row = this.#db.prepare('SELECT 1 AS hit FROM links WHERE code = ? COLLATE BINARY').get(code);
    return row !== undefined;
  }
}
