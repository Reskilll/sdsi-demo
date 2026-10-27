export type AgentId =
  | 'lead' | 'research' | 'audit' | 'tech' | 'speed' | 'mobile' | 'a11y' | 'ux' | 'geo'
  | 'redesign' | 'bench' | 'deck';

/** Plain names that say what each agent does. */
export const PERSONAS: Record<AgentId, { name: string; emoji: string; role: string }> = {
  lead: { name: 'Coordinator', emoji: '🧭', role: 'Plans and runs the whole job' },
  research: { name: 'Market Researcher', emoji: '📰', role: 'Reads the latest news on the company' },
  audit: { name: 'Site Auditor', emoji: '🕵️', role: 'Checks the website' },
  tech: { name: 'Tech Detector', emoji: '🧩', role: 'Finds the technologies in use' },
  speed: { name: 'Speed Tester', emoji: '⏱️', role: 'Measures page speed' },
  mobile: { name: 'Mobile Tester', emoji: '📱', role: 'Checks the site on a phone' },
  a11y: { name: 'Accessibility Checker', emoji: '♿', role: 'Checks it works for everyone' },
  ux: { name: 'UX Reviewer', emoji: '👁️', role: 'Reviews usability and design' },
  geo: { name: 'AI-Search Checker', emoji: '🔎', role: 'Checks visibility in AI search' },
  redesign: { name: 'Designer', emoji: '🎨', role: 'Builds the new homepage' },
  bench: { name: 'Team Matcher', emoji: '🧑‍💻', role: 'Finds our available people' },
  deck: { name: 'Deck Writer', emoji: '📊', role: 'Writes the pitch deck and proposal' },
};

export type FeedKind =
  | 'plan' | 'status' | 'finding' | 'handoff' | 'question' | 'answer'
  | 'tool_start' | 'tool_end' | 'skill_start' | 'skill_end'
  | 'partial_result' | 'warning' | 'done' | 'error' | 'usage';

/** Tokens one model call used, and what they cost. Posted as a 'usage' event (not shown in the feed). */
export interface TokenUsage {
  model: string;
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  /** USD at list price; null when the model's price is unknown. */
  costUsd: number | null;
}

/** A finished result, posted as its own formatted card. */
export interface FeedCard {
  title: string;
  headline: string;
  score?: number;
  grade?: string;
  metrics?: Record<string, string | number>;
  tone?: 'good' | 'warn' | 'bad';
  /** A technology id: the feed shows its logo next to the title. */
  icon?: string;
}

export interface FeedEvent {
  id: number;
  ts: number;
  runId: string;
  from: AgentId;
  /** 'human' marks an escalation: something the agents may not decide alone. */
  to?: AgentId | 'all' | 'human';
  kind: FeedKind;
  /** One short, human-friendly line. */
  friendly: string;
  /** The serious layer, shown on expand. */
  detail?: { summary: string; data?: unknown; evidence?: string[] };
  tool?: { name: string; callId: string; durationMs?: number; ok?: boolean; attempt?: number };
  progress?: { step: number; of: number };
  /** A screenshot taken during the run (URL under /runs/<id>/). */
  image?: string;
  /** A finished result shown as a card. */
  card?: FeedCard;
  /** A headline number, shown large in the feed. */
  stat?: { value: string; label: string; tone?: 'good' | 'warn' | 'bad' };
  /** Token usage of one model call (kind 'usage'). */
  usage?: TokenUsage;
  /** Partial result payload that fills a UI panel. */
  panel?: { name: string; data: unknown };
}

export type NewEvent = Omit<FeedEvent, 'id' | 'ts' | 'runId'>;

export class RunBus {
  readonly events: FeedEvent[] = [];
  private listeners = new Set<(e: FeedEvent) => void>();
  constructor(readonly runId: string) {}

  emit(e: NewEvent): FeedEvent {
    const full: FeedEvent = { ...e, id: this.events.length + 1, ts: Date.now(), runId: this.runId };
    this.events.push(full);
    for (const l of this.listeners) l(full);
    return full;
  }

  subscribe(fn: (e: FeedEvent) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
}
