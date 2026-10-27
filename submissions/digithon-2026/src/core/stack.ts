import type { NetRequest, StackReport, StackSkill, TrafficStats } from './types.js';
import type { Tech } from './techSignatures.js';
import type { OrgSkill } from './orgMatch.js';
import { registrable } from './domain.js';

const TYPE_LABEL: Record<string, string> = { Document: 'Page (HTML)', Script: 'JavaScript', Stylesheet: 'CSS', Image: 'Images', Font: 'Fonts', XHR: 'Data calls', Fetch: 'Data calls', Media: 'Video & audio' };

/** What a HAR summary would show: weight and request count by type, third-party share, busiest domains. */
export function trafficStats(network: NetRequest[]): TrafficStats {
  const byType = new Map<string, { requests: number; bytes: number }>();
  const byHost = new Map<string, { requests: number; bytes: number; thirdParty: boolean }>();
  let tpReq = 0, tpBytes = 0, bytes = 0, failed = 0;
  for (const r of network) {
    const label = TYPE_LABEL[r.type] ?? 'Other';
    const t = byType.get(label) ?? { requests: 0, bytes: 0 }; t.requests++; t.bytes += r.bytes; byType.set(label, t);
    const h = byHost.get(registrable(r.host)) ?? { requests: 0, bytes: 0, thirdParty: r.thirdParty }; h.requests++; h.bytes += r.bytes; byHost.set(registrable(r.host), h);
    bytes += r.bytes; if (r.thirdParty) { tpReq++; tpBytes += r.bytes; } if (r.status >= 400) failed++;
  }
  return {
    totalRequests: network.length, totalBytes: bytes, failedRequests: failed, uniqueDomains: byHost.size,
    thirdParty: { requests: tpReq, bytes: tpBytes, requestShare: network.length ? Math.round((100 * tpReq) / network.length) : 0, byteShare: bytes ? Math.round((100 * tpBytes) / bytes) : 0 },
    byType: [...byType.entries()].map(([type, v]) => ({ type, ...v })).sort((a, b) => b.bytes - a.bytes),
    topDomains: [...byHost.entries()].map(([domain, v]) => ({ domain, ...v })).sort((a, b) => b.bytes - a.bytes).slice(0, 8),
  };
}

/** How well our organisation covers each detected technology. strong: skilled and 2+ free; partial: some capacity; gap: nobody free. */
export function stackCoverage(techs: Tech[], inventory: OrgSkill[]): { skills: StackSkill[]; score: number } {
  const seen = new Set<string>();
  const skills: StackSkill[] = [];
  for (const t of techs) {
    if (!t.skill || seen.has(t.id)) continue;
    seen.add(t.id);
    const sk = inventory.find((s) => s.id === t.skill);
    const status: StackSkill['status'] = !sk || sk.available === 0 ? 'gap' : sk.available >= 2 && sk.level >= 3 ? 'strong' : 'partial';
    skills.push({ techId: t.id, tech: t.name, category: t.category, skillId: t.skill, skillLabel: sk?.label ?? t.skill, level: sk?.level ?? 0, headcount: sk?.headcount ?? 0, available: sk?.available ?? 0, availableFrom: sk?.availableFrom ?? null, status });
  }
  const pts = { strong: 1, partial: 0.6, gap: 0 };
  const score = skills.length ? Math.round((100 * skills.reduce((a, s) => a + pts[s.status], 0)) / skills.length) : 0;
  return { skills, score };
}
