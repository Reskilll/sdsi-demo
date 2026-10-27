import { defineTool } from '../core/tool.js';
import { computeOrgMatch, hardcodedProvider, neededSkills, type Developer } from '../core/orgMatch.js';
import type { DevMatch, Finding, MatchResult } from '../core/types.js';

const DAYS_BY_SEVERITY = { 1: 2, 2: 4, 3: 7 } as const;
const CATEGORY_NAME: Record<string, string> = { speed: 'Performance engineering', mobile: 'Responsive & mobile fixes', a11y: 'Accessibility remediation', ux: 'UX & conversion redesign', geo: 'Structured data & AI-search' };
const MARGIN = 1.4;

export const rosterLoad = defineTool({
  name: 'roster.load',
  feed: {
    start: ['Opening the talent roster. Who is available?', 'Checking who is between projects.'],
    end: (r: { devs: Developer[] }) => `${r.devs.length} developers on the roster; ${r.devs.filter((d) => d.availableFrom <= '2026-11-09').length} free within two weeks.`,
    error: 'The roster sheet would not open.',
  },
  run: async () => ({ devs: hardcodedProvider.developers() }),
});

export const orgMatch = defineTool({
  name: 'skill.org-match',
  kind: 'skill',
  feed: {
    start: ['Counting how many of the skills we need we actually have…', 'The Team Matcher is lining up our skills against their needs.'],
    end: (r: ReturnType<typeof computeOrgMatch>) => `Organisation match: ${r.score}/100. ${r.gaps.length ? `Gap: ${r.gaps.slice(0, 2).join(', ')}.` : 'No real gaps.'}`,
    error: 'The skill matrix refused to add up.',
    card: (r) => ({ title: 'Organisation match', score: r.score, headline: r.gaps.length ? `Gaps: ${r.gaps.slice(0, 3).join(', ')}.` : 'No real gaps for this prospect.', metrics: { Strengths: r.strengths.slice(0, 3).join(', ') || 'none', Skills: r.breakdown.length }, tone: r.score >= 85 ? 'good' : r.score >= 65 ? 'warn' : 'bad' }),
    detail: (r) => `Score = 100 x sum(weight x (0.6 x proficiency + 0.4 x depth)) / sum(weight). Strengths: ${r.strengths.join(', ') || 'none'}. Gaps: ${r.gaps.join(', ') || 'none'}.`,
  },
  run: async ({ findings, stack }: { findings: Finding[]; stack?: { skill?: string; category: string }[] }) => computeOrgMatch(neededSkills(findings, stack), hardcodedProvider.skills()),
});

interface TeamOut { team: DevMatch[]; weeks: number; estimate: MatchResult['estimate']; idleCostRecovered: number }

export const teamMatch = defineTool({
  name: 'skill.team-match',
  kind: 'skill',
  feed: {
    start: ['Picking the dream team from whoever is free…', 'Matching real people to real problems.'],
    end: (r: TeamOut) => `Dream team of ${r.team.length}, ready to start ${r.team.map((t) => t.availableFrom).sort()[0]}. About ${r.weeks} weeks of work.`,
    error: 'The team sheet got scrambled.',
    detail: (r) => r.team.map((t) => `${t.name} (${t.role}, fit ${Math.round(t.fit * 100)}%)`).join('; '),
  },
  run: async ({ findings, weights }: { findings: Finding[]; weights: Record<string, number> }): Promise<TeamOut> => {
    const devs = hardcodedProvider.developers();
    // Effort by workstream, driven by what the audit found.
    const byCat = new Map<string, number>();
    for (const f of findings) byCat.set(f.category, (byCat.get(f.category) ?? 0) + DAYS_BY_SEVERITY[f.severity]);
    const workstreams = [...byCat.entries()].map(([c, days]) => ({ name: CATEGORY_NAME[c], days }));
    workstreams.unshift({ name: 'Homepage rebuild (design + front end)', days: 15 });
    const build = workstreams.reduce((a, w) => a + w.days, 0);
    workstreams.push({ name: 'QA & launch', days: Math.ceil(build * 0.15) }, { name: 'Delivery management', days: Math.ceil(build * 0.1) });
    const totalDays = workstreams.reduce((a, w) => a + w.days, 0);

    // Greedy pick: best-fit free developer for each needed skill, heaviest skills first.
    const chosen = new Map<string, DevMatch>();
    const skillsByWeight = Object.entries(weights).sort((a, b) => b[1] - a[1]);
    for (const [skill, w] of skillsByWeight) {
      if (chosen.size >= 6) break;
      const cand = devs.filter((d) => d.skills.includes(skill) && !chosen.has(d.id))
        .sort((a, b) => b.level - a.level || a.availableFrom.localeCompare(b.availableFrom))[0];
      if (!cand) continue;
      const covered = cand.skills.filter((s) => s in weights);
      const coverage = covered.reduce((a, s) => a + weights[s], 0) / Object.values(weights).reduce((a, b) => a + b, 0);
      const fit = Math.min(1, 0.55 * (cand.level / 5) + 0.45 * Math.min(1, coverage * 3));
      chosen.set(cand.id, { id: cand.id, name: cand.name, role: cand.role, level: cand.level, fit: +fit.toFixed(2), skills: covered, availableFrom: cand.availableFrom,
        rationale: `Level ${cand.level}/5 in ${covered.join(', ')}; free from ${cand.availableFrom}. Needed for ${skill} (weight ${w.toFixed(1)}).` });
    }
    const team = [...chosen.values()].sort((a, b) => b.fit - a.fit);
    const rate = team.length ? devs.filter((d) => chosen.has(d.id)).reduce((a, d) => a + d.dayRate, 0) / team.length : 8000;
    const weeks = Math.max(2, Math.ceil(totalDays / Math.max(1, team.length) / 5));
    const base = totalDays * rate * MARGIN;
    const est: MatchResult['estimate'] = {
      workstreams, totalDays, weeks, priceLow: Math.round((base * 0.9) / 1000) * 1000, priceHigh: Math.round((base * 1.15) / 1000) * 1000, currency: hardcodedProvider.currency(),
      assumptions: ['Homepage and key templates only; no new backend features', 'Client provides brand assets and timely feedback', `Blended day rate ${Math.round(rate)} with a ${Math.round((MARGIN - 1) * 100)}% margin`, 'Estimate is +/- range until discovery is complete'],
    };
    return { team, estimate: est, weeks, idleCostRecovered: Math.round(team.length * weeks * 5 * rate * 0.6) };
  },
});

import type { RunContext } from '../core/context.js';

export async function runBench(run: RunContext): Promise<MatchResult> {
  const audit = run.data.audit;
  if (!audit) throw new Error('Team match needs the audit first.');
  const findings = audit.categories.flatMap((c) => c.findings);
  const weights = neededSkills(findings, audit && run.data.stack?.technologies ? run.data.stack.technologies : []);
  run.bus.emit({ from: 'bench', kind: 'status', friendly: 'Reading the problem list. Which skills does this job need?', detail: { summary: `Needed skills (weight): ${Object.entries(weights).map(([k, v]) => `${k} ${v.toFixed(1)}`).join(', ')}` } });
  await rosterLoad({}, { run, agent: 'bench' });
  const org = await orgMatch({ findings, stack: run.data.stack?.technologies }, { run, agent: 'bench' });
  const t = await teamMatch({ findings, weights }, { run, agent: 'bench' });
  const result: MatchResult = { orgScore: org.score, skills: org.breakdown, strengths: org.strengths, gaps: org.gaps, team: t.team, estimate: t.estimate, idleCostRecovered: t.idleCostRecovered };
  run.data.match = result;
  const earliest = t.team.map((d) => d.availableFrom).sort()[0];
  run.bus.emit({
    from: 'bench', to: 'lead', kind: 'partial_result',
    friendly: `Team assembled: ${t.team.length} people, org match ${org.score}/100${org.gaps.length ? `, honest gap in ${org.gaps[0]}` : ''}. Can start ${earliest}.`,
    panel: { name: 'team', data: result },
  });
  return result;
}
