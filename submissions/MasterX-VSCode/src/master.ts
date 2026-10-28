import {
  ClaudeCliError,
  ClaudeCliResult,
  parseJsonResult,
  runClaudeCli,
  truncate,
} from './claudeCli';
import { LogFn, MasterPlan, SubTask, TaskAction, TaskResult } from './types';

/** Actions the Master is allowed to emit. */
const VALID_ACTIONS: TaskAction[] = ['create_file', 'edit_file', 'run_command'];

/** Planning is pure reasoning; no tools. */
const PLAN_TOOLS: string[] = [];

/** Synthesis is pure reasoning over the Worker's logs; no tools. */
const REVIEW_TOOLS: string[] = [];

/** JSON Schema passed to `--json-schema` so the CLI structurally validates the plan. */
const PLAN_SCHEMA: Record<string, unknown> = {
  type: 'object',
  properties: {
    thought: {
      type: 'string',
      description: 'Your reasoning about how to approach the goal.',
    },
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          action: {
            type: 'string',
            enum: VALID_ACTIONS,
            description: 'What the Worker must do.',
          },
          targetPath: {
            type: 'string',
            description: 'Workspace-relative file path, or a short label for run_command.',
          },
          instructions: {
            type: 'string',
            description: 'Complete, self-contained specification for the Worker.',
          },
        },
        required: ['action', 'targetPath', 'instructions'],
      },
    },
  },
  required: ['thought', 'tasks'],
};

export interface MasterOptions {
  /** Resolved path to the `claude` executable. */
  cliPath: string;
  /** Workspace directory the Master runs in. */
  cwd: string;
  /** Model id for the Master (the deep-thinking model). */
  model: string;
  /** Run-scoped settings.json (model ids + OpenAI API key) for this run. */
  settingsPath?: string;
  /** Aborting this signal stops in-flight CLI calls when the run is stopped. */
  signal?: AbortSignal;
  log?: LogFn;
}

/**
 * The Master: a separate `claude` CLI instance bound to the deep-thinking
 * model. It reads only the Worker's dense summary (never raw source), emits a
 * strict JSON execution plan, and later synthesizes the final report from the
 * Worker's execution logs.
 */
export class Master {
  private readonly cliPath: string;
  private readonly cwd: string;
  private readonly model: string;
  private readonly settingsPath: string | undefined;
  private readonly signal: AbortSignal | undefined;
  private readonly log: LogFn;

  constructor(options: MasterOptions) {
    this.cliPath = options.cliPath;
    this.cwd = options.cwd;
    this.model = options.model;
    this.settingsPath = options.settingsPath;
    this.signal = options.signal;
    this.log = options.log ?? (() => undefined);

    if (!this.model || !this.model.trim()) {
      throw new ClaudeCliError('Master: model id is empty. Set `masterx.masterModel`.');
    }
  }

  /** The model id this Master is bound to (shown in the status bar). */
  get modelId(): string {
    return this.model;
  }

  /**
   * Stage 2: given the user's goal and the Worker's dense codebase summary,
   * produce a strict JSON execution plan of SubTasks.
   */
  async plan(goal: string, denseIndexSummary: string): Promise<MasterPlan> {
    const system =
      'You are the planning Master in a Master-Worker code-generation pipeline, running as a ' +
      'separate Claude CLI instance with a deep-thinking model. ' +
      'You never see raw source code — only a dense architectural summary produced by a cheaper ' +
      'Worker — and you never write code yourself. Your job is to reason deeply about ' +
      'the user goal and emit a precise, ordered execution plan that the Worker can follow ' +
      'without any further context.\n\n' +
      'Each task must be self-contained: a Worker who has seen nothing else must be able to ' +
      'execute it from your instructions alone. Specify file paths, function names, signatures, ' +
      'behavior, error handling, and integration points explicitly.\n\n' +
      'Rules:\n' +
      '- Order tasks so dependencies are built before their consumers.\n' +
      '- Prefer create_file over edit_file when writing substantial new code.\n' +
      '- Use run_command only for build/install/test steps (npm install, npm run compile, etc.).\n' +
      '- Do not include verification fluff — every task must change the workspace or run a command.\n' +
      '- Output only the JSON object described by the schema. No markdown fences, no commentary.';

    const prompt =
      `USER GOAL:\n${goal.trim()}\n\n` +
      `WORKER CODEBASE SUMMARY (the only view of the codebase you get):\n${denseIndexSummary.trim()}\n\n` +
      'Produce the execution plan JSON now.';

    const outcome = await runPlan({
      cliPath: this.cliPath,
      cwd: this.cwd,
      model: this.model,
      settingsPath: this.settingsPath,
      signal: this.signal,
      prompt,
      system,
      log: this.log,
    });

    this.logFor(outcome, 'plan');
    return this.parsePlan(outcome.result);
  }

  /**
   * Stage 4: evaluate the Worker's execution results and write a clear final
   * report for the user.
   */
  async synthesize(goal: string, results: TaskResult[]): Promise<string> {
    const system =
      'You are the reviewing Master in a Master-Worker code-generation pipeline. ' +
      'The Worker has finished executing the plan you previously issued. Review the execution ' +
      'results and write a clear, concise final report for the user.\n\n' +
      'The report must cover:\n' +
      '1. What was accomplished relative to the original goal (or why the goal could not be met).\n' +
      '2. The files created/modified and commands run.\n' +
      '3. Any failures or deviations, stated plainly.\n' +
      '4. What the user should do next.\n\n' +
      'Write plain prose with short section headings. Do not restate raw logs. Do not use JSON.';

    const resultBlock = results
      .map((r) => {
        const status = r.success ? 'OK' : 'FAILED';
        const body = r.success ? r.output : `${r.output}${r.error ? `\nERROR: ${r.error}` : ''}`;
        return `[${status}] ${r.action} → ${r.targetPath}\n${truncate(body, 2_500)}`;
      })
      .join('\n\n');

    const prompt =
      `ORIGINAL GOAL:\n${goal.trim()}\n\n` +
      `EXECUTION RESULTS (${results.length} tasks):\n${resultBlock || '(no tasks were executed)'}\n\n` +
      'Write the final report now.';

    const outcome = await runClaudeCli({
      cliPath: this.cliPath,
      cwd: this.cwd,
      model: this.model,
      settingsPath: this.settingsPath,
      role: 'master',
      prompt,
      system,
      tools: REVIEW_TOOLS,
      allowedTools: [],
      timeoutMs: 10 * 60 * 1000,
      signal: this.signal,
      log: this.log,
    });

    this.logFor(outcome, 'synthesis');
    return outcome.result.trim();
  }

  /**
   * Parse and validate the strict JSON plan the Master is required to emit.
   * Tolerates a stray ```json fence and leading/trailing prose.
   */
  private parsePlan(text: string): MasterPlan {
    const parsed = parseJsonResult(text, 'Master plan');
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new ClaudeCliError('Master plan JSON must be an object with "thought" and "tasks".');
    }

    const obj = parsed as { thought?: unknown; tasks?: unknown };
    const thought = typeof obj.thought === 'string' ? obj.thought.trim() : '';
    if (!Array.isArray(obj.tasks)) {
      throw new ClaudeCliError('Master plan is missing a "tasks" array.');
    }

    const tasks: SubTask[] = [];
    for (let i = 0; i < obj.tasks.length; i++) {
      const raw = obj.tasks[i] as {
        action?: unknown;
        targetPath?: unknown;
        instructions?: unknown;
      };
      const action = typeof raw?.action === 'string' ? raw.action.trim() : '';
      const targetPath = typeof raw?.targetPath === 'string' ? raw.targetPath.trim() : '';
      const instructions = typeof raw?.instructions === 'string' ? raw.instructions.trim() : '';

      if (!VALID_ACTIONS.includes(action as TaskAction)) {
        throw new ClaudeCliError(
          `Master plan task ${i + 1} has invalid action "${action}". Expected one of: ${VALID_ACTIONS.join(', ')}.`
        );
      }
      if (!targetPath) {
        throw new ClaudeCliError(`Master plan task ${i + 1} is missing "targetPath".`);
      }
      if (!instructions) {
        throw new ClaudeCliError(`Master plan task ${i + 1} (${targetPath}) is missing "instructions".`);
      }

      tasks.push({
        id: `T${i + 1}`,
        action: action as TaskAction,
        targetPath,
        instructions,
      });
    }

    return { thought, tasks };
  }

  private logFor(outcome: ClaudeCliResult, label: string): void {
    this.log(
      `Master ${label} finished: ${outcome.output_tokens} output tokens, ` +
        `$${outcome.total_cost_usd.toFixed(4)}, ${Math.round(outcome.durationMs / 1000)}s.`,
      'debug'
    );
  }
}

/** Convenience wrapper that runs the plan request through the shared CLI runner. */
async function runPlan(options: {
  cliPath: string;
  cwd: string;
  model: string;
  settingsPath?: string;
  signal?: AbortSignal;
  prompt: string;
  system: string;
  log?: LogFn;
}): Promise<ClaudeCliResult> {
  return runClaudeCli({
    cliPath: options.cliPath,
    cwd: options.cwd,
    model: options.model,
    settingsPath: options.settingsPath,
    role: 'master',
    prompt: options.prompt,
    system: options.system,
    tools: PLAN_TOOLS,
    allowedTools: [],
    jsonSchema: PLAN_SCHEMA,
    timeoutMs: 15 * 60 * 1000,
    signal: options.signal,
    log: options.log,
  });
}
