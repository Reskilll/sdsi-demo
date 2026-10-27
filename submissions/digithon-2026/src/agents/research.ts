import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { RunContext } from '../core/context.js';
import type { NewEvent } from '../core/events.js';

/** One signal about the company: a news item or a market trend, and what we could do about it. */
export interface ResearchItem { kind: 'news' | 'trend'; title: string; headline: string; tone: 'good' | 'warn' | 'bad'; angle: string }
export interface ResearchBrief { company: string; domains: string[]; sources: string[]; items: ResearchItem[]; summary: string }

const DIR = join(process.cwd(), 'config', 'research');

/**
 * The imported market-research brief for a website, if there is one (config/research/*.json, matched on domain).
 * Today the briefs are imported files; a web-search step can replace this later without changing the feed.
 */
export function loadBrief(url: string, dir = DIR): ResearchBrief | null {
  let host = '';
  try { host = new URL(/^https?:/.test(url) ? url : `https://${url}`).hostname.replace(/^www\./, ''); } catch { return null; }
  let files: string[] = [];
  try { files = readdirSync(dir).filter((f) => f.endsWith('.json')); } catch { return null; }
  for (const f of files) {
    const b = JSON.parse(readFileSync(join(dir, f), 'utf8')) as ResearchBrief;
    if (b.domains?.some((d) => host === d || host.endsWith(`.${d}`))) return b;
  }
  return null;
}

/** The feed posts for a brief, in order, each with the pause before it (ms). Shared by live runs and by the trace import. */
export function researchEvents(b: ResearchBrief): { gapMs: number; ev: NewEvent }[] {
  const news = b.items.filter((i) => i.kind === 'news').length, trends = b.items.length - news;
  const call = { name: 'skill.research', callId: 'research-1' };
  return [
    { gapMs: 900, ev: { from: 'lead', to: 'research', kind: 'handoff', friendly: `Market Researcher, find out what is happening at ${b.company} right now, before we look at the site.` } },
    { gapMs: 700, ev: { from: 'research', kind: 'skill_start', friendly: `Reading the latest news, analyst notes and market reports on ${b.company}…`, tool: call } },
    ...b.items.map((it) => ({ gapMs: 1600, ev: {
      from: 'research' as const, kind: 'finding' as const, friendly: `${it.kind === 'news' ? 'In the news' : 'Market trend'}: ${it.title}.`,
      card: { title: it.title, headline: it.headline, tone: it.tone, metrics: { Type: it.kind === 'news' ? 'News' : 'Trend', 'What we can do': it.angle } },
      detail: { summary: `${it.headline}\nWhat we can do: ${it.angle}\nSources read: ${b.sources.join(', ')}.` },
    } })),
    { gapMs: 1400, ev: {
      from: 'research', kind: 'skill_end', friendly: `Research done: ${b.items.length} signals that shape the pitch.`, tool: { ...call, durationMs: 1400 + b.items.length * 1600, ok: true },
      card: { title: 'Market research', headline: b.summary, tone: 'warn', metrics: { Signals: b.items.length, News: news, Trends: trends } },
      detail: { summary: b.summary },
    } },
    { gapMs: 300, ev: { from: 'research', to: 'lead', kind: 'partial_result', friendly: `Research brief ready for ${b.company}.`, panel: { name: 'research', data: b } } },
    { gapMs: 900, ev: { from: 'research', to: 'lead', kind: 'answer', friendly: `Coordinator, here is the angle: ${b.items.map((i) => i.angle.toLowerCase()).slice(0, 2).join('; ')}.`, detail: { summary: b.items.map((i) => `${i.title}: ${i.angle}`).join('\n') } } },
  ];
}

/** Runs the research step of a live run: posts the brief one signal at a time, then hands the angle to the Coordinator. */
export async function runResearch(run: RunContext, brief: ResearchBrief, wait = (ms: number) => new Promise((r) => setTimeout(r, ms))): Promise<void> {
  for (const { gapMs, ev } of researchEvents(brief)) { await wait(gapMs); run.bus.emit(ev); }
  run.data.research = brief;
}

/**
 * Puts the research posts into a saved trace, right after the Coordinator's opening plan, and moves the later posts back
 * by the time the research takes. Earlier research posts are removed first, so running it twice changes nothing.
 */
export function withResearch<T extends { id: number | string; ts: number; runId: string; from: string; to?: string; researchShiftMs?: number }>(trace: T[], b: ResearchBrief): T[] {
  const kept = trace.filter((e) => e.from !== 'research' && e.to !== 'research');
  if (!kept.length) return trace;
  // Undo the shift of an earlier import (recorded on the opening post), so the timing is the same however often it runs.
  const prev = kept[0].researchShiftMs ?? 0;
  const base = kept.map((e, i) => (i === 0 ? e : { ...e, ts: e.ts - prev }));
  const steps = researchEvents(b), total = steps.reduce((a, s) => a + s.gapMs, 0) + 900;
  let t = base[0].ts;
  const added = steps.map(({ gapMs, ev }) => { t += gapMs; return { ...ev, ts: t, runId: base[0].runId } as unknown as T; });
  const out = [{ ...base[0], researchShiftMs: total }, ...added, ...base.slice(1).map((e) => ({ ...e, ts: e.ts + total }))];
  return out.map((e, i) => ({ ...e, id: i + 1 }));
}
