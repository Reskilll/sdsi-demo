import type { RunContext } from '../core/context.js';
import { llmAvailable, llmText } from '../core/llm.js';
import { runAudit } from './audit.js';
import { runBench } from './bench.js';
import { runDeck } from './deck.js';
import { runRedesign } from './redesign.js';
import { loadBrief, runResearch } from './research.js';
import { NEVER_ALONE, type Escalation } from '../core/policy.js';
import { LlmPlanner, MAX_STEPS, RulePlanner, STEPS, type Decision, type PlanState, type Planner, type StepId } from './planner.js';

export type Runners = Record<StepId, (run: RunContext, feedback?: string) => Promise<unknown>>;

export const defaultRunners: Runners = {
  audit: (run) => runAudit(run),
  redesign: (run, feedback) => runRedesign(run, feedback),
  bench: (run) => runBench(run),
  deck: (run) => runDeck(run),
};

/** Chooses the planner: a model when a key is set (unless forced to fixed), otherwise the rule policy. */
export function choosePlanner(run?: RunContext): Planner {
  if (process.env.NITRO_LEAD === 'fixed' || !llmAvailable) return new RulePlanner();
  return new LlmPlanner((system, user) => llmText(system, user, { maxTokens: 400, usage: run && { run, agent: 'lead' } }));
}

function stateOf(run: RunContext, completed: Set<StepId>, failed: Set<StepId>, attempts: Record<StepId, number>, stepsTaken: number): PlanState {
  const audit = run.data.audit;
  const weakest = audit ? [...audit.categories].sort((a, b) => a.score - b.score)[0]?.category : undefined;
  return {
    completed: [...completed], failed: [...failed], attempts: { ...attempts }, stepsTaken,
    facts: {
      overall: audit?.overall, weakest, topFixes: audit?.topFixes.map((f) => f.title),
      // Only meaningful regressions count: GEO is re-checked at page level only, and a template redesign cannot improve on a retry.
      regressions: run.data.prototype?.usedLLM ? run.data.prototype.reaudit.filter((r) => r.category !== 'geo' && r.after <= r.before - 5).map((r) => r.category) : undefined,
      llmAvailable,
    },
  };
}

const HANDOFF: Partial<Record<StepId, (run: RunContext, retry: boolean) => void>> = {
  redesign: (run, retry) => run.bus.emit({ from: 'lead', to: 'redesign', kind: 'handoff',
    friendly: retry ? 'Designer, that one scored worse in places. Take another pass.' : `Designer, here are the ${run.data.audit?.topFixes.length ?? 0} problems to fix. Make it beautiful.`,
    detail: { summary: (run.data.audit?.topFixes ?? []).map((f) => f.title).join('\n') } }),
  bench: (run) => run.bus.emit({ from: 'lead', to: 'bench', kind: 'handoff', friendly: 'Team Matcher, find us the right people for these problems.' }),
  deck: (run) => run.bus.emit({ from: 'lead', to: 'deck', kind: 'handoff', friendly: 'Deck Writer, everything is in. Make it send-ready.' }),
};

/**
 * The lead agent's loop: ask the planner what to do next, run those steps (in parallel when several),
 * record the outcome, repeat. Failures degrade gracefully; the audit failing is the only fatal case.
 */
export async function executePlan(run: RunContext, planner: Planner, runners: Runners = defaultRunners): Promise<void> {
  const host = (() => { try { return new URL(/^https?:/.test(run.url) ? run.url : `https://${run.url}`).hostname; } catch { return run.url; } })();
  run.bus.emit({
    from: 'lead', to: 'all', kind: 'plan', friendly: `New case! Let's see what we can do for ${host}. Everyone to your stations.`,
    detail: { summary: `Planner: ${planner.name}. Steps available: ${STEPS.join(', ')}. Budget: ${MAX_STEPS} planning rounds.\nNever allowed alone:\n${NEVER_ALONE.map((p) => `- ${p.rule}`).join('\n')}`, data: { neverAlone: NEVER_ALONE } },
  });

  // First step of the journey: what is happening at the company right now (only when a brief is imported for this site).
  const brief = loadBrief(run.url);
  if (brief) await runResearch(run, brief);

  const completed = new Set<StepId>(), failed = new Set<StepId>();
  const attempts: Record<StepId, number> = { audit: 0, redesign: 0, bench: 0, deck: 0 };
  let stepsTaken = 0;

  for (;;) {
    const state = stateOf(run, completed, failed, attempts, stepsTaken);
    const decision: Decision = await planner.next(state);
    run.bus.emit({
      from: 'lead', kind: 'status', friendly: decision.reason,
      detail: { summary: `Decision (${decision.source}): ${decision.action}${decision.steps.length ? ' ' + decision.steps.join(' + ') : ''}`, data: decision },
    });
    if (decision.action === 'finish' || stepsTaken >= MAX_STEPS) break;
    stepsTaken++;

    for (const step of decision.steps) HANDOFF[step]?.(run, attempts[step] > 0);
    const feedback = decision.steps.includes('redesign') && attempts.redesign > 0
      ? `Scores dropped in: ${state.facts.regressions?.join(', ')}.` : undefined;
    for (const step of decision.steps) attempts[step]++;
    const results = await Promise.allSettled(decision.steps.map((step) => runners[step](run, feedback)));
    results.forEach((r, i) => {
      const step = decision.steps[i];
      if (r.status === 'fulfilled') { completed.add(step); failed.delete(step); return; }
      failed.add(step);
      if (step === 'audit') run.bus.emit({ from: 'lead', kind: 'error', friendly: `The audit failed, so there is nothing to build on. ${r.reason instanceof Error ? r.reason.message : ''}` });
      else run.bus.emit({ from: step, kind: 'warning', friendly: `${step} hit a wall. Carrying on with what we have.`, detail: { summary: String(r.reason) } });
    });
    if (failed.has('audit')) throw new Error('Audit failed');
  }

  // The agents stop here and hand the decisions they may not take alone to a person, each with its reason.
  for (const e of escalations(run, completed, failed)) run.bus.emit({ from: 'lead', to: 'human', kind: 'question', friendly: `Needs a human: ${e.reason}`, detail: { summary: e.detail } });

  const secs = Math.round((Date.now() - run.startedAt) / 1000);
  const used = run.bus.events.flatMap((e) => (e.usage ? [e.usage] : []));
  if (used.length) {
    const tokens = used.reduce((a, u) => a + u.input + u.output + u.cacheRead + u.cacheWrite, 0);
    const cost = used.every((u) => u.costUsd != null) ? used.reduce((a, u) => a + (u.costUsd ?? 0), 0) : null;
    run.bus.emit({ from: 'lead', kind: 'status', friendly: `This run used ${tokens.toLocaleString('en-US')} model tokens${cost != null ? `, about $${cost.toFixed(3)}` : ''}.`,
      stat: { value: cost != null ? `$${cost.toFixed(3)}` : `${tokens.toLocaleString('en-US')}`, label: cost != null ? `model cost of this run (${tokens.toLocaleString('en-US')} tokens)` : 'model tokens used' },
      detail: { summary: `${used.length} model calls. Input ${used.reduce((a, u) => a + u.input, 0)}, output ${used.reduce((a, u) => a + u.output, 0)}, cache read ${used.reduce((a, u) => a + u.cacheRead, 0)}, cache write ${used.reduce((a, u) => a + u.cacheWrite, 0)} tokens.` } });
  }
  run.bus.emit({ from: 'lead', kind: 'done', friendly: `All done in ${secs}s. A human reviews before anything is sent.`, detail: { summary: `Run ${run.runId} finished in ${secs}s. Completed: ${[...completed].join(', ')}. Failed: ${[...failed].join(', ') || 'none'}.` } });
}

/** What a person must decide before this pitch goes anywhere. Always ends with the approval nobody else may give. */
export function escalations(run: RunContext, completed: Set<StepId>, failed: Set<StepId>): Escalation[] {
  const out: Escalation[] = [];
  if (run.data.injection?.length) out.push({ reason: 'the website contains text aimed at AI assistants.', detail: `The page ${run.data.injection.join('; ')}. It was treated as data and scores were range-checked, but check the UX and AI-search results by eye before using them.` });
  for (const step of failed) if (!completed.has(step)) out.push({ reason: `the ${step} step failed.`, detail: 'The rest of the pitch was built without it. Decide whether to re-run the analysis or continue.' });
  const gaps = run.data.match?.gaps ?? [];
  if (gaps.length) out.push({ reason: `we cannot fully staff ${gaps.slice(0, 3).join(', ')}.`, detail: 'The agents will not promise skills we do not have. Decide whether to pitch anyway, bring in a partner, or hire.' });
  if (run.data.prototype && !run.data.prototype.usedLLM && llmAvailable) out.push({ reason: 'the redesign is the template version.', detail: 'The model could not produce a usable page, so the offline template was used. Check it represents their brand before showing it.' });
  out.push({ reason: 'approve every screen before anything is sent.', detail: 'Nothing goes to the client automatically. Review each screen, then submit for Knox approval.' });
  return out;
}

export async function runLead(run: RunContext): Promise<void> {
  return executePlan(run, choosePlanner(run));
}
