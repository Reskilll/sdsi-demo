/**
 * Link service: the single place where the business rules live.
 *
 * Everything here is synchronous (better-sqlite3) and free of Express types, so
 * the same code path is exercised by unit tests, integration tests and the HTTP
 * layer.
 *
 * Concurrency: writes run inside `db.transaction(...).immediate()`, which takes
 * SQLite's RESERVED lock *before* the lookup. That serialises the read-then-insert
 * sequence across processes, so two simultaneous requests for the same URL can
 * never produce two codes (requirement M4). The partial unique index is the
 * backstop if a future refactor loses the transaction.
 */

import type { Database as DatabaseType } from 'better-sqlite3';

import { generateCode } from '../domain/base62.js';
import { validateAlias } from '../domain/alias.js';
import { AppError } from '../domain/errors.js';
import { parseExpiresAt, toIso, toUtcDate } from '../domain/expiry.js';
import { normalizeUrl } from '../domain/url.js';
import type {
  CreateLinkInput,
  CreateLinkResult,
  DailyClicksEntry,
  LinkRow,
  LinkStats,
  LinkSummary,
  ListLinksResult,
  NewClick,
} from '../domain/types.js';
import { ClicksRepository } from '../db/clicks.repo.js';
import { LinksRepository } from '../db/links.repo.js';
import type { Clock } from '../lib/clock.js';
import { hashIp, truncate } from '../lib/crypto.js';
import type { Logger } from '../lib/logger.js';

export interface LinkServiceOptions {
  db: DatabaseType;
  clock: Clock;
  logger: Logger;
  publicBaseUrl: string;
  codeLength: number;
  maxUrlLength: number;
  allowPrivateHosts: boolean;
  selfOrigins: readonly string[];
  expiryMaxDays: number;
  ipSalt: string;
  /** How many distinct codes to try when a generated code collides. */
  maxCodeAttempts?: number;
}

export interface ClickContext {
  ip?: string | undefined;
  userAgent?: string | undefined;
  referer?: string | undefined;
}

const MAX_ATTEMPTS_DEFAULT = 8;
const MAX_UA_LENGTH = 512;
const MAX_REFERER_LENGTH = 512;

/** `SqliteError` shape we care about: UNIQUE constraint violation. */
function isUniqueViolation(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    typeof (error as { code?: unknown }).code === 'string' &&
    ((error as { code: string }).code === 'SQLITE_CONSTRAINT_UNIQUE' ||
      (error as { code: string }).code === 'SQLITE_CONSTRAINT_PRIMARYKEY')
  );
}

export class LinkService {
  readonly #db: DatabaseType;
  readonly #links: LinksRepository;
  readonly #clicks: ClicksRepository;
  readonly #clock: Clock;
  readonly #logger: Logger;
  readonly #options: Required<Omit<LinkServiceOptions, 'db' | 'clock' | 'logger' | 'selfOrigins'>> & {
    selfOrigins: readonly string[];
  };

  constructor(options: LinkServiceOptions) {
    this.#db = options.db;
    this.#links = new LinksRepository(options.db);
    this.#clicks = new ClicksRepository(options.db);
    this.#clock = options.clock;
    this.#logger = options.logger;
    this.#options = {
      publicBaseUrl: options.publicBaseUrl,
      codeLength: options.codeLength,
      maxUrlLength: options.maxUrlLength,
      allowPrivateHosts: options.allowPrivateHosts,
      selfOrigins: options.selfOrigins,
      expiryMaxDays: options.expiryMaxDays,
      ipSalt: options.ipSalt,
      maxCodeAttempts: options.maxCodeAttempts ?? MAX_ATTEMPTS_DEFAULT,
    };
  }

  /** Builds the absolute short URL returned to clients. */
  shortUrlFor(code: string): string {
    return `${this.#options.publicBaseUrl}/${code}`;
  }

  /**
   * Create (or idempotently return) a short link.
   *
   * - Same URL twice, no alias -> same code, `created: false` (M4).
   * - Same URL, previously expired -> a fresh code is minted; the old code keeps
   *   returning 410 so historical stats stay attributable.
   * - Custom alias: unique namespace, no dedupe, 409 when taken (M4 exemption).
   */
  createLink(input: CreateLinkInput): CreateLinkResult {
    const now = this.#clock.now();
    const normalized = normalizeUrl(input.url, {
      maxUrlLength: this.#options.maxUrlLength,
      allowPrivateHosts: this.#options.allowPrivateHosts,
      selfOrigins: this.#options.selfOrigins,
    });

    const aliasProvided = input.alias !== undefined && input.alias !== null && input.alias !== '';
    const alias = aliasProvided ? validateAlias(input.alias) : null;

    const expiresAt =
      input.expiresAt === undefined || input.expiresAt === null || input.expiresAt === ''
        ? null
        : parseExpiresAt(input.expiresAt, now, this.#options.expiryMaxDays);

    const run = this.#db.transaction((): CreateLinkResult => {
      if (alias) {
        return this.#createWithAlias(alias, normalized.url, normalized.hash, now, expiresAt);
      }
      return this.#createOrReuse(normalized.url, normalized.hash, now, expiresAt);
    });

    // `.immediate()` acquires the write lock up front; reads inside the callback
    // therefore cannot race with another creator.
    return run.immediate();
  }

  #createWithAlias(
    alias: string,
    url: string,
    urlHash: string,
    now: number,
    expiresAt: number | null,
  ): CreateLinkResult {
    const existing = this.#links.findByAliasAndUrl(alias, urlHash);
    if (existing) {
      if (existing.expires_at !== null && existing.expires_at <= now) {
        throw new AppError(
          'ALIAS_TAKEN',
          'Alias already belongs to an expired link; choose another alias',
          { field: 'alias', alias, reason: 'expired' },
        );
      }
      return { link: existing, shortUrl: this.shortUrlFor(existing.code), created: false };
    }

    if (this.#links.codeExists(alias)) {
      throw new AppError('ALIAS_TAKEN', 'Alias is already in use', { field: 'alias', alias });
    }

    try {
      const link = this.#links.insert({
        code: alias,
        url,
        urlHash,
        alias: true,
        createdAt: now,
        expiresAt,
      });
      return { link, shortUrl: this.shortUrlFor(link.code), created: true };
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new AppError('ALIAS_TAKEN', 'Alias is already in use', { field: 'alias', alias });
      }
      throw error;
    }
  }

  #createOrReuse(
    url: string,
    urlHash: string,
    now: number,
    expiresAt: number | null,
  ): CreateLinkResult {
    // M4: reuse a live link for the same canonical URL regardless of expiry
    // differences; otherwise mint a new code.
    const live = this.#links.findLiveByHash(urlHash, now);
    if (live) {
      return { link: live, shortUrl: this.shortUrlFor(live.code), created: false };
    }

    for (let attempt = 0; attempt < this.#options.maxCodeAttempts; attempt += 1) {
      const code = generateCode(this.#options.codeLength);
      try {
        const link = this.#links.insert({
          code,
          url,
          urlHash,
          alias: false,
          createdAt: now,
          expiresAt,
        });
        return { link, shortUrl: this.shortUrlFor(link.code), created: true };
      } catch (error) {
        if (!isUniqueViolation(error)) throw error;
        // Either the generated code collided (retry) or a concurrent insert beat
        // us to the dedupe index. Re-check the dedupe row before retrying.
        const raced = this.#links.findLiveByHash(urlHash, now);
        if (raced) {
          return { link: raced, shortUrl: this.shortUrlFor(raced.code), created: false };
        }
        this.#logger.warn({ attempt, code }, 'generated code collision, retrying');
      }
    }

    throw new AppError(
      'CODE_GENERATION_FAILED',
      'Could not allocate a unique short code, please retry',
    );
  }

  /**
   * Resolve a code for redirecting (M2).
   *
   * @throws AppError LINK_GONE (410) for expired/deleted, LINK_NOT_FOUND (404).
   */
  resolve(code: string, context: ClickContext = {}): LinkRow {
    const link = this.#links.findByCodeIncludingDeleted(code);
    if (!link) {
      throw new AppError('LINK_NOT_FOUND', 'Short code not found', { code });
    }
    if (link.deleted_at !== null) {
      throw new AppError('LINK_GONE', 'Short link has been deleted', { code });
    }

    const now = this.#clock.now();
    if (link.expires_at !== null && link.expires_at <= now) {
      throw new AppError('LINK_GONE', 'Short link has expired', {
        code,
        expiredAt: toIso(link.expires_at),
      });
    }

    return link;
  }

  /**
   * Record a click (M5). Deliberately fail-open: analytics must never break the
   * redirect, so failures are logged and swallowed.
   */
  recordClick(code: string, context: ClickContext = {}): void {
    const click: NewClick = {
      code,
      clickedAt: this.#clock.now(),
      ipHash: hashIp(context.ip ?? null, this.#options.ipSalt),
      userAgent: truncate(context.userAgent, MAX_UA_LENGTH),
      referer: truncate(context.referer, MAX_REFERER_LENGTH),
    };

    try {
      const write = this.#db.transaction(() => {
        this.#clicks.insert(click);
        this.#links.incrementClicks(code, click.clickedAt);
      });
      write();
    } catch (error) {
      this.#logger.warn({ err: error, code }, 'failed to record click; redirect continues');
    }
  }

  /** Aggregate stats for a code (M5). Unknown codes are 404. */
  getStats(code: string): LinkStats {
    const link = this.#links.findByCodeIncludingDeleted(code);
    if (!link) {
      throw new AppError('LINK_NOT_FOUND', 'Short code not found', { code });
    }

    const now = this.#clock.now();
    const totals = this.#clicks.totals(code);
    const perDay = this.#clicks.perDay(code);

    return {
      code: link.code,
      url: link.url,
      createdAt: toIso(link.created_at) ?? '',
      expiresAt: toIso(link.expires_at),
      deletedAt: toIso(link.deleted_at),
      expired: link.expires_at !== null && link.expires_at <= now,
      totalClicks: totals.total,
      uniqueVisitors: totals.uniqueVisitors,
      lastAccessedAt: toIso(totals.last),
      firstAccessedAt: toIso(totals.first),
      clicksPerDay: buildDenseSeries(perDay, totals.first ?? link.created_at, now),
      clickDays: perDay.length,
    };
  }

  /** Recent individual clicks, newest first (dashboard detail view). */
  recentClicks(code: string, limit = 20) {
    const link = this.#links.findByCodeIncludingDeleted(code);
    if (!link) {
      throw new AppError('LINK_NOT_FOUND', 'Short code not found', { code });
    }
    return this.#clicks.recent(code, clampInteger(limit, 1, 100)).map((row) => ({
      clickedAt: toIso(row.clicked_at) ?? '',
      userAgent: row.user_agent,
      referer: row.referer,
    }));
  }

  /** Paginated link listing for the dashboard. */
  listLinks(limit: number, offset: number): ListLinksResult {
    const safeLimit = clampInteger(limit, 1, 100);
    const safeOffset = clampInteger(offset, 0, Number.MAX_SAFE_INTEGER);
    const now = this.#clock.now();

    const rows = this.#links.list(safeLimit, safeOffset);
    return {
      items: rows.map((row) => this.#toSummary(row, now)),
      total: this.#links.count(),
      limit: safeLimit,
      offset: safeOffset,
    };
  }

  #toSummary(row: LinkRow, now: number): LinkSummary {
    return {
      code: row.code,
      shortUrl: this.shortUrlFor(row.code),
      url: row.url,
      createdAt: toIso(row.created_at) ?? '',
      expiresAt: toIso(row.expires_at),
      expired: row.expires_at !== null && row.expires_at <= now,
      clickCount: row.click_count,
      lastAccessedAt: toIso(row.last_accessed_at),
    };
  }

  /**
   * Soft-delete a link; the code resolves to 410 afterwards and stats remain
   * readable so historical numbers are not lost (M2).
   */
  deleteLink(code: string): void {
    const now = this.#clock.now();
    const removed = this.#links.softDelete(code, now);
    if (removed === 0) {
      const existing = this.#links.findByCodeIncludingDeleted(code);
      if (!existing) {
        throw new AppError('LINK_NOT_FOUND', 'Short code not found', { code });
      }
      // Already deleted: treat as idempotent success.
      return;
    }
    this.#logger.info({ code }, 'link soft-deleted');
  }

  /** Remove long-expired links (maintenance command). */
  purgeExpired(olderThanDays: number): number {
    const now = this.#clock.now();
    const cutoff = now - olderThanDays * 86_400_000;
    return this.#links.purgeExpiredBefore(cutoff);
  }

  /** Health probe: cheap query that proves the database is readable/writable. */
  checkDatabase(): { ok: boolean; schemaVersion: number } {
    const row = this.#db.prepare('SELECT MAX(id) AS version FROM schema_migrations').get() as
      | { version: number | null }
      | undefined;
    return { ok: true, schemaVersion: row?.version ?? 0 };
  }
}

/**
 * Expand sparse per-day counts into a dense, gap-filled series so charts do not
 * need to infer missing days. Range: first activity day (or creation day) through
 * the current UTC day, capped to keep responses small.
 */
export function buildDenseSeries(
  buckets: ReadonlyArray<{ day: string; clicks: number }>,
  startMs: number,
  nowMs: number,
  maxDays = 366,
): DailyClicksEntry[] {
  const counts = new Map(buckets.map((bucket) => [bucket.day, bucket.clicks]));
  const startDay = toUtcDate(startMs);
  const endDay = toUtcDate(Math.max(nowMs, startMs));

  const series: DailyClicksEntry[] = [];
  let cursor = Date.parse(`${startDay}T00:00:00.000Z`);
  const end = Date.parse(`${endDay}T00:00:00.000Z`);

  while (cursor <= end) {
    const day = toUtcDate(cursor);
    series.push({ date: day, clicks: counts.get(day) ?? 0 });
    cursor += 86_400_000;
  }

  return series.length > maxDays ? series.slice(-maxDays) : series;
}

/** Coerce and clamp a numeric query parameter. */
export function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  const integer = Math.trunc(value);
  if (integer < min) return min;
  if (integer > max) return max;
  return integer;
}
