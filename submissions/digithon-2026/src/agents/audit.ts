import type { RunContext } from '../core/context.js';
import { grade } from '../core/scoring.js';
import * as browser from '../tools/browser.js';
import { techDetect } from '../tools/tech.js';
import { a11yInspect, geoInspect, mobileInspect, speedInspect, uxReview } from '../tools/inspectors.js';
import type { AgentId } from '../core/events.js';
import { injectionSignals } from '../core/guard.js';
import type { AuditReport, CategoryResult, Finding } from '../core/types.js';

const WEIGHTS: Record<string, number> = { speed: 0.2, mobile: 0.2, a11y: 0.2, ux: 0.25, geo: 0.15 };

export async function runAudit(run: RunContext): Promise<AuditReport> {
  const say = (friendly: string, extra: object = {}) => run.bus.emit({ from: 'audit', kind: 'status', friendly, ...extra });
  say('Audit desk is open. First, a proper look at the site.');
  const blockedBefore = browser.blockedRequests;
  const crawl = await browser.browserRender({ url: run.url, dir: run.dir }, { run, agent: 'audit' });
  const blocked = browser.blockedRequests - blockedBefore;
  if (blocked > 0) run.bus.emit({ from: 'audit', kind: 'warning', friendly: `Blocked ${blocked} request${blocked > 1 ? 's' : ''} from the page to private or internal addresses.`, detail: { summary: 'Guardrail: the crawler never reaches private networks, even when a public page redirects or points there (src/core/ssrf.ts).' } });
  run.data.crawl = crawl;
  // Guardrail: page text is data. If it tries to instruct an AI, say so now; the Coordinator escalates it to a human.
  const pageText = [crawl.title, crawl.description, ...crawl.h1s, crawl.heroText, crawl.bodySample, ...crawl.nav.map((n) => n.text), ...crawl.ctas.map((c) => c.text)].join('\n');
  run.data.injection = injectionSignals(pageText);
  if (run.data.injection.length) run.bus.emit({ from: 'audit', kind: 'warning', friendly: 'Heads up: this page contains text aimed at AI assistants. Treating it as data only.', detail: { summary: `The page ${run.data.injection.join('; ')}. Model calls wrap page text as untrusted data and their scores are range-checked; a human is asked to look before anything is sent.` } });

  run.bus.emit({ from: 'audit', to: 'all', kind: 'handoff', friendly: 'Got the page. Five inspectors and the tech detector, go! Everyone gets the same snapshot.', detail: { summary: 'Crawl data shared with the speed, mobile, accessibility, UX and AI-search inspectors; all run in parallel.' } });

  const input = { crawl, dir: run.dir };
  const jobs: [AgentId, Promise<CategoryResult>][] = [
    ['speed', speedInspect(input, { run, agent: 'speed' })],
    ['mobile', mobileInspect(input, { run, agent: 'mobile' })],
    ['a11y', a11yInspect(input, { run, agent: 'a11y' })],
    ['ux', uxReview(input, { run, agent: 'ux' })],
    ['geo', geoInspect(input, { run, agent: 'geo' })],
  ];
  const techJob = techDetect({ crawl }, { run, agent: 'tech' });
  const settled = await Promise.allSettled(jobs.map(([, p]) => p));
  await techJob.then((stack) => {
    run.data.stack = stack;
    run.bus.emit({ from: 'tech', to: 'lead', kind: 'partial_result', friendly: `Tech stack mapped: ${stack.technologies.length} technologies, ${stack.coverage.score}% covered by our team.`, panel: { name: 'stack', data: stack } });
  }).catch((e) => run.bus.emit({ from: 'tech', kind: 'warning', friendly: 'Could not map the tech stack, carrying on without it.', detail: { summary: String(e) } }));
  const categories = settled.flatMap((s, i) => {
    if (s.status === 'fulfilled') return [s.value];
    run.bus.emit({ from: jobs[i][0], kind: 'warning', friendly: 'Could not finish this inspection, carrying on without it.', detail: { summary: String(s.reason) } });
    return [];
  });
  if (!categories.length) throw new Error('All inspectors failed.');

  const wsum = categories.reduce((a, c) => a + WEIGHTS[c.category], 0);
  const overall = Math.round(categories.reduce((a, c) => a + c.score * WEIGHTS[c.category], 0) / wsum);

  // Top fixes: severity first, at most two per category so the list is balanced.
  const perCat: Record<string, number> = {};
  const topFixes: Finding[] = categories.flatMap((c) => c.findings)
    .sort((a, b) => b.severity - a.severity || (WEIGHTS[b.category] - WEIGHTS[a.category]))
    .filter((f) => (perCat[f.category] = (perCat[f.category] ?? 0) + 1) <= 2).slice(0, 5);

  // Headline numbers, shown large in the feed as each score lands.
  const NAMES: Record<string, string> = { speed: 'speed', mobile: 'mobile', a11y: 'accessibility', ux: 'UX', geo: 'AI-search' };
  for (const c of categories) run.bus.emit({ from: c.category as AgentId, kind: 'status', friendly: `${NAMES[c.category]} score: ${c.score}/100 (grade ${c.grade}).`, stat: { value: String(c.score), label: `${NAMES[c.category]} score`, tone: c.score >= 80 ? 'good' : c.score >= 65 ? 'warn' : 'bad' } });
  const report: AuditReport = { overall, grade: grade(overall), categories, topFixes };
  run.data.audit = report;
  const worst = [...categories].sort((a, b) => a.score - b.score)[0];
  run.bus.emit({
    from: 'audit', to: 'lead', kind: 'finding',
    friendly: `Report card is in: ${overall}/100, grade ${report.grade}. Weakest spot: ${worst.category} (${worst.grade}).`,
    detail: { summary: categories.map((c) => `${c.category}: ${c.score} (${c.grade}) - ${c.headline}`).join('\n') },
    panel: { name: 'audit', data: { ...report, screenshot: `/runs/${run.runId}/shot-desktop.png`, mobileShot: `/runs/${run.runId}/shot-mobile.png`, url: crawl.finalUrl, title: crawl.title } },
  });
  topFixes.forEach((f, i) => run.bus.emit({ from: f.category as AgentId, to: 'lead', kind: 'finding', friendly: `Fix #${i + 1}: ${f.title}.`, detail: { summary: `${f.evidence}\nFix: ${f.fix}\nWhy it matters: ${f.impact}`, evidence: [f.evidence] } }));
  return report;
}
