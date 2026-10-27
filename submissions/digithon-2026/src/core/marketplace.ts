import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { z } from 'zod';
import { PERSONAS } from './events.js';

/** live = in the app today, beta = partly built, planned = on the roadmap. */
export const STATUSES = ['live', 'beta', 'planned'] as const;
export const CATEGORIES = ['Coordinate', 'Research', 'Audit', 'Test', 'Build', 'People', 'Sell', 'Always on'] as const;

const ListingSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/),
  name: z.string().min(1),
  emoji: z.string().min(1),
  status: z.enum(STATUSES),
  category: z.enum(CATEGORIES),
  summary: z.string().min(1),
  inputs: z.array(z.string()).min(1),
  outputs: z.array(z.string()).min(1),
  builtWith: z.array(z.string()),
  showcase: z.string().min(1),
});
export type Listing = z.infer<typeof ListingSchema>;

/**
 * Checks the catalogue: ids are unique, and every agent that runs in the app is listed as live,
 * so the marketplace never shows a working agent as planned (or forgets one).
 */
export function validateCatalogue(raw: unknown): Listing[] {
  const agents = z.object({ agents: z.array(ListingSchema) }).parse(raw).agents;
  const seen = new Set<string>();
  for (const a of agents) {
    if (seen.has(a.id)) throw new Error(`Duplicate marketplace id: ${a.id}`);
    seen.add(a.id);
  }
  for (const id of Object.keys(PERSONAS)) {
    const a = agents.find((x) => x.id === id);
    if (a?.status !== 'live') throw new Error(`Agent ${id} runs in the app but is not listed as live in the marketplace`);
  }
  return agents;
}

export function loadMarketplace(): Listing[] {
  return validateCatalogue(JSON.parse(readFileSync(join(process.cwd(), 'config/marketplace.json'), 'utf8')));
}

/** Counts per status and category, shown in the marketplace header. */
export function marketplaceSummary(agents: Listing[]) {
  const count = <K extends string>(keys: readonly K[], pick: (a: Listing) => K) => Object.fromEntries(keys.map((k) => [k, agents.filter((a) => pick(a) === k).length])) as Record<K, number>;
  return { total: agents.length, byStatus: count(STATUSES, (a) => a.status), byCategory: count(CATEGORIES, (a) => a.category) };
}
