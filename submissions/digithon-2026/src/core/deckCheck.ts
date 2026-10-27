import JSZip from 'jszip';

/** The text of each slide in a .pptx, in slide order. */
export async function slideTexts(buf: Buffer): Promise<string[]> {
  const zip = await JSZip.loadAsync(buf);
  const names = Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n)).sort((a, b) => Number(a.match(/\d+/g)!.at(-1)) - Number(b.match(/\d+/g)!.at(-1)));
  const unescape = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
  return Promise.all(names.map(async (n) => [...(await zip.files[n].async('string')).matchAll(/<a:t>([^<]*)<\/a:t>/g)].map((m) => unescape(m[1])).join(' ').replace(/\s+/g, ' ').trim()));
}

export interface DeckCheckItem { area: string; item: string; found: boolean; slides: number[]; add: string }
export interface DeckCheck { file: string; uploadedAt: number; slides: number; covered: number; total: number; checks: DeckCheckItem[] }

/** What the run found, in the shape this check needs (all optional: a run may not have every section). */
export interface Analysis {
  audit?: { overall: number; grade: string; categories: { category: string; score: number }[]; topFixes: { category: string; title: string }[] };
  stack?: { technologies?: { name: string }[] };
  prototype?: { reaudit?: { category: string; before: number; after: number }[] };
  team?: { orgScore: number; team?: unknown[]; price?: unknown };
  research?: { items: { title: string; angle: string }[] };
}

const AREA: Record<string, [string, RegExp]> = {
  speed: ['Speed', /\b(speed|load(ing)? time|performance|lighthouse|core web vitals|lcp)\b/i],
  mobile: ['Mobile', /\b(mobile|phone|tap targets?|responsive)\b/i],
  a11y: ['Accessibility', /\b(accessib\w*|wcag|screen reader|a11y)\b/i],
  ux: ['UX', /\b(ux|usability|user experience|design|call to action|cta)\b/i],
  geo: ['AI search', /\b(ai search|structured data|schema|llms\.txt|seo)\b/i],
};
const STOP = new Set(['the', 'and', 'are', 'for', 'from', 'with', 'that', 'this', 'into', 'their', 'have', 'has', 'more', 'most', 'lost', 'spot', 'local']);
const words = (t: string) => t.toLowerCase().split(/[^a-z0-9.]+/).filter((w) => w.length > 3 && !STOP.has(w));

/**
 * Checks an uploaded deck against the analysis we already have: which findings, technologies, research signals,
 * redesign results and team details it covers, on which slides, and what to add. Plain text matching, no model.
 */
export function checkDeck(texts: string[], a: Analysis, file: string): DeckCheck {
  const at = (re: RegExp) => texts.flatMap((t, i) => (re.test(t) ? [i + 1] : []));
  const checks: DeckCheckItem[] = [];
  const push = (area: string, item: string, slides: number[], add: string) => checks.push({ area, item, found: slides.length > 0, slides, add });
  if (a.research) for (const r of a.research.items) {
    const ws = words(r.title), hits = texts.flatMap((t, i) => (ws.filter((w) => t.toLowerCase().includes(w)).length >= Math.min(2, ws.length) ? [i + 1] : []));
    push('Market research', r.title, hits, `Open with this signal and our answer: ${r.angle}.`);
  }
  if (a.audit) {
    push('Site audit', `Site score ${a.audit.overall}/100 (grade ${a.audit.grade})`, at(new RegExp(`\\b${a.audit.overall}\\s*(/\\s*100|out of 100)`)), `Add the site score, ${a.audit.overall}/100, with the five category scores.`);
    for (const c of a.audit.categories) {
      const [name, re] = AREA[c.category] ?? [c.category, new RegExp(c.category, 'i')];
      const fix = a.audit.topFixes.find((f) => f.category === c.category);
      push('Site audit', `${name}: ${c.score}/100`, at(re), `Add the ${name.toLowerCase()} finding${fix ? `: ${fix.title}` : ''}.`);
    }
  }
  const tech = a.stack?.technologies ?? [];
  if (tech.length) {
    const hits = tech.filter((t) => texts.some((x) => x.toLowerCase().includes(t.name.toLowerCase())));
    push('Tech stack', `Their technologies (${hits.length} of ${tech.length} named)`, hits.length >= Math.ceil(tech.length / 2) ? at(new RegExp(hits.map((h) => h.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'i')) : [],
      `Name their stack (${tech.slice(0, 5).map((t) => t.name).join(', ')}…) and how our people cover it.`);
  }
  if (a.prototype?.reaudit?.length) push('Redesign', 'Before and after of their homepage', at(/\b(redesign\w*|before|after|new homepage|concept)\b/i), `Add the before/after: ${a.prototype.reaudit.map((r) => `${AREA[r.category]?.[0] ?? r.category} ${r.before} → ${r.after}`).join(', ')}.`);
  if (a.team) {
    push('Team', `Named team (organisation match ${a.team.orgScore}/100)`, at(/\b(team|experts?|developers?|our people)\b/i), 'Add the named team of available experts and the organisation match.');
    push('Estimate', 'Effort, timeline and price', at(/\b(price|cost|investment|estimate|timeline|person-days|weeks)\b/i), 'Add the estimate: effort, timeline and price range.');
  }
  const covered = checks.filter((c) => c.found).length;
  return { file, uploadedAt: Date.now(), slides: texts.length, covered, total: checks.length, checks };
}
