import type { AgentId, FeedCard } from './events.js';
import type { RunContext } from './context.js';

export interface ToolCtx {
  run: RunContext;
  agent: AgentId;
}

export interface FeedSpec<I, O> {
  /** Pool of fun "starting" lines; rotated so repeats don't get stale within a run. */
  start: string[];
  /** Built from the real result so numbers are always true. */
  end: (result: O, input: I) => string;
  error: string;
  /** Serious layer shown on expand. */
  detail?: (result: O) => string;
  evidence?: (result: O) => string[];
  /** A formatted result card, posted as its own new post when the tool finishes. */
  card?: (result: O) => FeedCard;
}

export interface ToolSpec<I, O> {
  name: string;
  kind?: 'tool' | 'skill';
  feed: FeedSpec<I, O>;
  retries?: number;
  run: (input: I, ctx: ToolCtx) => Promise<O>;
}

let callCounter = 0;

/**
 * Every tool and skill goes through here, so each execution posts to the live feed
 * automatically (start, end, retry, failure). A tool without a `feed` spec does not compile.
 */
export function defineTool<I, O>(spec: ToolSpec<I, O>) {
  const kind = spec.kind ?? 'tool';
  const retries = spec.retries ?? 1;

  const call = async (input: I, ctx: ToolCtx): Promise<O> => {
    const callId = `${spec.name}#${++callCounter}`;
    const { run, agent } = ctx;
    const line =
      spec.feed.start.find((l) => !run.usedStartLines.has(l)) ?? spec.feed.start[callCounter % spec.feed.start.length];
    run.usedStartLines.add(line);

    run.bus.emit({
      from: agent, kind: `${kind}_start`, friendly: line,
      tool: { name: spec.name, callId, attempt: 1 },
    });
    const t0 = Date.now();

    for (let attempt = 1; ; attempt++) {
      try {
        const result = await spec.run(input, ctx);
        const durationMs = Date.now() - t0;
        run.bus.emit({
          from: agent, kind: `${kind}_end`, friendly: spec.feed.end(result, input),
          detail: spec.feed.detail
            ? { summary: spec.feed.detail(result), evidence: spec.feed.evidence?.(result) }
            : undefined,
          card: spec.feed.card?.(result),
          tool: { name: spec.name, callId, durationMs, ok: true, attempt },
        });
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (attempt <= retries) {
          run.bus.emit({
            from: agent, kind: 'warning', friendly: `${spec.feed.error} Trying again.`,
            detail: { summary: msg }, tool: { name: spec.name, callId, ok: false, attempt },
          });
          continue;
        }
        run.bus.emit({
          from: agent, kind: `${kind}_end`, friendly: `${spec.feed.error} Giving up on this one.`,
          detail: { summary: msg }, tool: { name: spec.name, callId, durationMs: Date.now() - t0, ok: false, attempt },
        });
        throw err;
      }
    }
  };
  call.spec = spec;
  return call;
}
