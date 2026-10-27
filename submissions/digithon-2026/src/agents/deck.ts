import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { RunContext } from '../core/context.js';
import { defineTool } from '../core/tool.js';
import type { DeckResult } from '../core/types.js';
import { buildClientDeck } from './clientDeck.js';

const inr = (n: number) => '₹' + new Intl.NumberFormat('en-IN').format(n);

export const buildDeck = defineTool({
  name: 'skill.deck',
  kind: 'skill',
  feed: {
    start: ['The Deck Writer is arranging the slides…', 'Turning findings into a story the CMO will read.'],
    end: (r: DeckResult) => `Deck and proposal are ready: ${r.pptx}.`,
    error: 'The slide master had a meltdown.',
    detail: () => 'Every number in the deck is read from the run context (audit, prototype, match); nothing is typed by hand.',
  },
  run: async (_: object, { run }): Promise<DeckResult> => {
    const { crawl, audit, brand, prototype, match } = run.data;
    if (!crawl || !audit || !brand || !match) throw new Error('Deck needs audit, brand kit and match.');
    // The slide deck itself lives in clientDeck.ts (Samsung SDS look, full audit, stack, team and estimate detail).
    const pptxName = 'pitch-deck.pptx';
    await buildClientDeck({ brandName: brand.name, url: crawl.finalUrl, audit, match, prototype, stack: run.data.stack, dir: run.dir, date: new Date().toISOString().slice(0, 10) }, join(run.dir, pptxName));

    const md = `# Proposal: ${brand.name} homepage improvement

## Where you are today
Overall score **${audit.overall}/100 (${audit.grade})** on speed, mobile, accessibility, UX and AI-search visibility.

${audit.categories.map((c) => `- **${c.category}**: ${c.score}/100 (${c.grade}). ${c.headline}`).join('\n')}

## Priority fixes
${audit.topFixes.map((f, i) => `${i + 1}. **${f.title}** — ${f.impact}\n   - Evidence: ${f.evidence}\n   - Fix: ${f.fix}`).join('\n')}

## Concept
A working prototype of the redesigned homepage is attached (prototype.html). Re-running the same inspectors: ${(prototype?.reaudit ?? []).map((r) => `${r.category} ${r.before}→${r.after}`).join(', ')}.

## Approach and timeline
${match.estimate.workstreams.map((w) => `- ${w.name}: ${w.days} days`).join('\n')}

Total: ${match.estimate.totalDays} person-days over about ${match.estimate.weeks} weeks.

## Team
Organisation skills match: **${match.orgScore}/100**.
${match.team.map((d) => `- ${d.name}, ${d.role} (free from ${d.availableFrom})`).join('\n')}

## Commercials
Estimated range: **${inr(match.estimate.priceLow)} – ${inr(match.estimate.priceHigh)}**.
Assumptions:
${match.estimate.assumptions.map((a) => `- ${a}`).join('\n')}

## Terms
_Placeholder: commercial terms to be added by the account owner before sending._
`;
    writeFileSync(join(run.dir, 'proposal.md'), md);
    return { pptx: pptxName, proposal: 'proposal.md' };
  },
});

export async function runDeck(run: RunContext): Promise<DeckResult> {
  run.bus.emit({ from: 'deck', kind: 'status', friendly: 'Everyone\'s work is in. Time to make it presentable.' });
  const d = await buildDeck({}, { run, agent: 'deck' });
  run.data.deck = d;
  run.bus.emit({
    from: 'deck', to: 'lead', kind: 'partial_result', friendly: 'Pitch deck and proposal are ready to review. Nothing gets sent until a human says so.',
    panel: { name: 'deck', data: { pptx: `/runs/${run.runId}/${d.pptx}`, proposal: `/runs/${run.runId}/${d.proposal}`, idleCostRecovered: run.data.match?.idleCostRecovered, priceLow: run.data.match?.estimate.priceLow } },
  });
  return d;
}
