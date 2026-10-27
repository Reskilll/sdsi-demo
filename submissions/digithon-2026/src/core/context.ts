import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { RunBus } from './events.js';
import type { ResearchBrief } from '../agents/research.js';
import type { AuditReport, BrandKit, CrawlData, MatchResult, Prototype, DeckResult, StackReport } from './types.js';

export interface RunData {
  research?: ResearchBrief;
  /** Why the page looks like it is addressing an AI (prompt injection); empty when nothing was found. */
  injection?: string[];
  crawl?: CrawlData;
  stack?: StackReport;
  audit?: AuditReport;
  brand?: BrandKit;
  prototype?: Prototype;
  match?: MatchResult;
  deck?: DeckResult;
}

export interface RunContext {
  runId: string;
  url: string;
  dir: string;
  bus: RunBus;
  data: RunData;
  startedAt: number;
  /** Base URL of this server, used to re-audit the generated prototype. */
  baseUrl: string;
  usedStartLines: Set<string>;
}

export function newRun(url: string, baseUrl: string): RunContext {
  const runId = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const dir = join(process.cwd(), 'runs', runId);
  mkdirSync(dir, { recursive: true });
  return { runId, url, dir, bus: new RunBus(runId), data: {}, startedAt: Date.now(), baseUrl, usedStartLines: new Set() };
}

/** Saves every feed event of the run. Replay mode streams this file, so viewing a past run never calls a model or a browser. */
export function saveTrace(run: RunContext): void {
  writeFileSync(join(run.dir, 'trace.json'), JSON.stringify(run.bus.events));
}
