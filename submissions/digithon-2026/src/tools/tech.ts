import { defineTool } from '../core/tool.js';
import { detectTech } from '../core/techSignatures.js';
import { stackCoverage, trafficStats } from '../core/stack.js';
import { hardcodedProvider } from '../core/orgMatch.js';
import type { CrawlData, StackReport } from '../core/types.js';

/** Pause between technology posts so each one can be read as it appears. */
const TECH_POST_GAP_MS = 700;
const mb = (b: number) => (b / 1e6).toFixed(1);

export const techDetect = defineTool({
  name: 'skill.tech',
  kind: 'skill',
  feed: {
    start: ['Reading the site\'s network traffic like a flight recorder…', 'Looking under the bonnet: which technologies power this site?'],
    end: (r: StackReport) => `Found ${r.technologies.length} technologies across ${r.traffic.totalRequests} requests. We can support ${r.coverage.score}% of the platform stack.`,
    error: 'The traffic log would not open.',
    card: (r) => ({ title: 'Tech stack', headline: `${r.technologies.length} technologies found; we can support ${r.coverage.score}% of the platform stack.`, metrics: { Requests: r.traffic.totalRequests, 'Third-party': `${r.traffic.thirdParty.requestShare}%`, Domains: r.traffic.uniqueDomains, Coverage: `${r.coverage.score}%` }, tone: r.coverage.score >= 80 ? 'good' : r.coverage.score >= 60 ? 'warn' : 'bad' }),
    detail: (r) => r.technologies.map((t) => `${t.name} (${t.category}, ${t.confidence}): ${t.evidence.join('; ')}`).join('\n'),
  },
  retries: 0,
  run: async ({ crawl }: { crawl: CrawlData }, { run, agent }): Promise<StackReport> => {
    const technologies = detectTech({ headers: crawl.headers, cookieNames: crawl.cookieNames, html: crawl.html, globals: crawl.globals, network: crawl.network });
    const traffic = trafficStats(crawl.network);
    const coverage = stackCoverage(technologies, hardcodedProvider.skills());
    const stat = (value: string, label: string, friendly: string, tone?: 'good' | 'warn' | 'bad') => run.bus.emit({ from: agent, kind: 'status', friendly, stat: { value, label, tone } });
    stat(String(traffic.totalRequests), 'network requests', `The page made ${traffic.totalRequests} requests to ${traffic.uniqueDomains} different domains.`);
    stat(`${traffic.thirdParty.requestShare}%`, 'of requests are third-party', `${traffic.thirdParty.requestShare}% of requests (${mb(traffic.thirdParty.bytes)} MB) come from other companies' servers.`, traffic.thirdParty.requestShare > 60 ? 'warn' : undefined);
    stat(String(technologies.length), 'technologies detected', `Spotted ${technologies.length} technologies. Here they are, one by one.`);
    // One post per technology, paced so each can be read.
    const status = Object.fromEntries(coverage.skills.map((s) => [s.techId, s]));
    for (const t of technologies) {
      const c = status[t.id];
      await new Promise((r) => setTimeout(r, TECH_POST_GAP_MS));
      run.bus.emit({
        from: agent, kind: 'finding', friendly: `Found ${t.name} (${t.category}).`,
        card: {
          icon: t.id, title: t.name, headline: `${t.category} · ${t.confidence === 'confirmed' ? 'confirmed' : 'likely'}`,
          metrics: { Evidence: t.evidence[0] ?? '', ...(c ? { 'Our team': c.status === 'gap' ? `Gap: nobody free for ${c.skillLabel}` : `${c.available} of ${c.headcount} free (${c.skillLabel})` } : {}) },
          tone: c ? (c.status === 'strong' ? 'good' : c.status === 'partial' ? 'warn' : 'bad') : undefined,
        },
        detail: { summary: `Signals: ${t.evidence.join('; ')}` },
      });
    }
    const gaps = coverage.skills.filter((s) => s.status === 'gap');
    if (coverage.skills.length) stat(`${coverage.score}%`, 'of their stack we can support', gaps.length ? `We have no one free for: ${gaps.map((g) => g.tech).join(', ')}.` : 'We have people free for every mapped technology.', gaps.length ? 'warn' : 'good');
    return { technologies, traffic, coverage };
  },
});
