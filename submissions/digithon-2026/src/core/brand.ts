import { registrable } from './domain.js';

/**
 * The company name to put on the cover: prefer the title segment that matches the site's domain ("Samsung India" for
 * samsung.com), then the site's declared name, then the first short title segment, then the domain itself.
 */
export function inferBrandName(title: string, host: string, siteName?: string | null): string {
  const clean = (x: string) => x.toLowerCase().replace(/[^a-z0-9]/g, '');
  const bare = host.replace(/^www\./, '');
  const labels = [...new Set([bare.split('.')[0], registrable(bare).split('.')[0]].map(clean))].filter((l) => l.length > 2);
  const segs = title.split(/[|\-–—:·•]/).map((s) => s.trim()).filter((s) => s.length > 1 && s.length < 40);
  // A brand name is shorter than a tagline, so among the segments that mention the domain's name take the shortest.
  const byDomain = labels.map((l) => segs.filter((s) => clean(s).includes(l)).sort((a, b) => a.length - b.length)[0]).find(Boolean);
  const site = siteName && siteName.trim().length > 1 && siteName.trim().length < 40 ? siteName.trim() : undefined;
  const fallback = (labels[0] ?? clean(bare)).replace(/^./, (c) => c.toUpperCase());
  return byDomain ?? site ?? segs.find((s) => s.length < 28) ?? fallback;
}
