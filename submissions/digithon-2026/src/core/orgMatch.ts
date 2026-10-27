import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { clamp } from './scoring.js';
import type { Finding, SkillBreakdown } from './types.js';

export interface OrgSkill { id: string; label: string; level: number; headcount: number; available: number; availableFrom: string | null }
export interface Developer { id: string; name: string; role: string; level: number; skills: string[]; availableFrom: string; dayRate: number }

/** Swap this for an HRMS adapter later; callers only depend on the interface. */
export interface OrgSkillProvider { skills(): OrgSkill[]; developers(): Developer[]; currency(): string }

export const hardcodedProvider: OrgSkillProvider = {
  skills: () => JSON.parse(readFileSync(join(process.cwd(), 'config/org-skills.json'), 'utf8')).skills,
  developers: () => JSON.parse(readFileSync(join(process.cwd(), 'config/bench.json'), 'utf8')).developers,
  currency: () => JSON.parse(readFileSync(join(process.cwd(), 'config/bench.json'), 'utf8')).currency,
};

/** Baseline skills any redesign project needs, regardless of audit findings. */
const BASELINE: Record<string, number> = { nextjs: 0.8, 'responsive-ui': 0.7, 'ux-design': 0.7, 'qa-testing': 0.5, 'project-mgmt': 0.5 };
const NEEDED_LEVEL = 4;
const PROFICIENCY_WEIGHT = 0.6;
const DEPTH_WEIGHT = 0.4;

/** Categories whose technologies the project would touch directly (integrations, migration, platform work). */
const PLATFORM_CATEGORIES = new Set(['Commerce platform', 'CMS & experience', 'Marketing & campaign', 'Server & language']);

export function neededSkills(findings: Finding[], stack: { skill?: string; category: string }[] = []): Record<string, number> {
  const w: Record<string, number> = { ...BASELINE };
  // The prospect's own stack matters: we need people who can work with what they run.
  for (const t of stack) if (t.skill) w[t.skill] = Math.max(w[t.skill] ?? 0, PLATFORM_CATEGORIES.has(t.category) ? 0.7 : 0.4);
  const sev: Record<string, number> = {};
  for (const f of findings) for (const s of f.skills) sev[s] = (sev[s] ?? 0) + f.severity;
  for (const [s, total] of Object.entries(sev)) w[s] = Math.max(w[s] ?? 0, clamp(total / 6, 0.3, 1, ) );
  return w;
}

/** Deterministic and explainable: same findings in, same score out. */
export function computeOrgMatch(weights: Record<string, number>, inventory: OrgSkill[]) {
  const breakdown: SkillBreakdown[] = [];
  let num = 0, den = 0;
  for (const [id, weight] of Object.entries(weights)) {
    const sk = inventory.find((s) => s.id === id);
    const needed = weight >= 0.8 ? 2 : 1;
    const proficiency = sk ? Math.min(sk.level, NEEDED_LEVEL) / NEEDED_LEVEL : 0;
    const depth = sk ? Math.min(1, sk.available / needed) : 0;
    const fit = PROFICIENCY_WEIGHT * proficiency + DEPTH_WEIGHT * depth;
    num += weight * fit; den += weight;
    breakdown.push({ id, label: sk?.label ?? id, weight: +weight.toFixed(2), needed, available: sk?.available ?? 0, headcount: sk?.headcount ?? 0, level: sk?.level ?? 0, fit: +fit.toFixed(2), availableFrom: sk?.availableFrom ?? null });
  }
  breakdown.sort((a, b) => b.weight - a.weight);
  const score = den ? Math.round((100 * num) / den) : 0;
  return {
    score, breakdown,
    strengths: breakdown.filter((b) => b.fit >= 0.85).map((b) => b.label),
    gaps: breakdown.filter((b) => b.fit < 0.5).map((b) => b.label),
  };
}
