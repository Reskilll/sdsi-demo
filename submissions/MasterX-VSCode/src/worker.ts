import * as path from 'path';
import {
  ClaudeCliError,
  ClaudeCliResult,
  parseJsonResult,
  runClaudeCli,
  stripWrappingFences,
  truncate,
} from './claudeCli';
import { LogFn, SubTask } from './types';
import { IndexArtifacts, IndexState, slugify } from './indexer';

/** Cap on characters of raw file content sent to the Worker during indexing. */
const SAMPLE_CONTENT_CAP = 24_000;

/** Cap on characters of existing file content shown when editing. */
const EXISTING_CONTENT_CAP = 30_000;

/** Read-only tools: the Worker may inspect the codebase but never drive it. */
const INDEX_TOOLS = ['Read', 'Glob', 'Grep'];

/** Drafting is text-in/text-out; no tools needed. */
const DRAFT_TOOLS: string[] = [];

/** JSON Schema for the two-tier index + planner summary produced during indexing. */
const INDEX_SCHEMA: Record<string, unknown> = {
  type: 'object',
  properties: {
    summary: {
      type: 'string',
      description:
        'High-density architectural summary for the planner: purpose, languages/frameworks, ' +
        'directory layout, key modules and responsibilities, important types/exports, entry ' +
        'points, build tooling, conventions.',
    },
    index: {
      type: 'object',
      properties: {
        hld: {
          type: 'string',
          description: 'Concise system-wide High-Level Design in Markdown.',
        },
        features: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string', description: 'Feature name as shown in the features list.' },
              slug: {
                type: 'string',
                description: 'lowercase-hyphenated file name for docs/<slug>.md',
              },
              lld: {
                type: 'string',
                description:
                  'Feature-specific Low-Level Design in Markdown: actionable technical details ' +
                  'and logic flow for this feature only.',
              },
              files: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    path: {
                      type: 'string',
                      description: 'Workspace-relative source file path.',
                    },
                    description: {
                      type: 'string',
                      description:
                        'Strict one-line description of the file responsibility within this feature.',
                    },
                  },
                  required: ['path', 'description'],
                },
              },
            },
            required: ['name', 'slug', 'lld', 'files'],
          },
        },
      },
      required: ['hld', 'features'],
    },
  },
  required: ['summary', 'index'],
};

export interface WorkerOptions {
  /** Resolved path to the `claude` executable. */
  cliPath: string;
  /** Workspace directory the Worker runs in. */
  cwd: string;
  /** Model id for the Worker (a cheaper Claude CLI model than the Master's). */
  model: string;
  /** Run-scoped settings.json (model ids + OpenAI API key) for this run. */
  settingsPath?: string;
  /** Aborting this signal stops in-flight CLI calls when the run is stopped. */
  signal?: AbortSignal;
  log?: LogFn;
}

/**
 * The Worker: a separate `claude` CLI instance bound to a lighter model. It
 * does the high-volume work — walking the codebase into a dense summary, then
 * drafting complete file contents and commands to the Master's specification —
 * so the Master never has to read raw source or write boilerplate.
 */
export class Worker {
  private readonly cliPath: string;
  private readonly cwd: string;
  private readonly model: string;
  private readonly settingsPath: string | undefined;
  private readonly signal: AbortSignal | undefined;
  private readonly log: LogFn;

  constructor(options: WorkerOptions) {
    this.cliPath = options.cliPath;
    this.cwd = options.cwd;
    this.model = options.model;
    this.settingsPath = options.settingsPath;
    this.signal = options.signal;
    this.log = options.log ?? (() => undefined);

    if (!this.model || !this.model.trim()) {
      throw new ClaudeCliError('Worker: model id is empty. Set `masterx.workerModel`.');
    }
  }

  /** The model id this Worker is bound to (shown in the status bar). */
  get modelId(): string {
    return this.model;
  }

  /**
   * Stage 1 (Scout): maintain the hierarchical `.masterx/` index and return a
   * dense architectural summary the Master can plan from without reading raw
   * source.
   *
   * The caller checks `.masterx/` first and passes its state through: when an
   * index already exists the Worker updates it from the recorded changes
   * instead of regenerating it from a full source scan. Output is structured —
   * `summary` for the planner plus HLD/LLD index artifacts the orchestrator
   * writes to disk.
   *
   * The Worker is given read-only tools so it can spot-check files it wants to
   * understand better than the samples allow.
   */
  async indexAndSummarize(
    goal: string,
    fileList: string[],
    sampleContents: string,
    existing: IndexState
  ): Promise<{ summary: string; index: IndexArtifacts }> {
    const truncatedList = fileList.slice(0, 400);
    const listBlock =
      truncatedList.length > 0
        ? truncatedList.map((f) => `- ${f}`).join('\n')
        : '(workspace contains no files)';

    const sampleBlock =
      sampleContents.trim().length > 0
        ? sampleContents.slice(0, SAMPLE_CONTENT_CAP)
        : '(no sample file contents available)';

    const formatRules =
      'INDEX FORMAT (strict):\n' +
      '- The root index.md has exactly two sections: High-Level Design (HLD) — a concise, ' +
      'system-wide architectural overview — and Features — a clean list of every core feature.\n' +
      '- Each feature page docs/<slug>.md has exactly two sections: Low-Level Design (LLD) — ' +
      'feature-specific, actionable technical details and logic flow — and File Registry — a ' +
      'bulleted list of every source file involved, each carrying a strict one-line description ' +
      'of its responsibility within that feature.\n' +
      'RULES:\n' +
      '- Keep HLD (system-wide) and LLD (feature-specific) strictly separated.\n' +
      '- Every source file named in a feature must carry its single-sentence description.\n' +
      '- Descriptions are technical, concise, free of conversational fluff. No raw source dumps.\n';

    const system =
      'You are the indexing Worker in a Master-Worker code-generation pipeline, running as a ' +
      'separate Claude CLI instance with a lightweight model. You maintain a hierarchical ' +
      'two-tier Markdown source-code index under `.masterx/` and produce a dense architectural ' +
      'summary for a separate planning model.\n\n' +
      formatRules +
      '\nThe `summary` field must be a HIGH-DENSITY architectural summary of the codebase: purpose, ' +
      'languages/frameworks, directory layout, key modules and their responsibilities, important ' +
      'types/interfaces/exports, entry points, build tooling, and any conventions or constraints ' +
      'that would affect writing new code. The planner reads ONLY this summary — never the raw ' +
      'code — so every line must carry information.\n' +
      'You have Read, Glob and Grep available: use them sparingly to confirm details the samples ' +
      'leave ambiguous, then stop. Do not modify anything. Do not ask questions.\n' +
      'Output only the JSON object described by the schema.';

    const updateBlock = existing.exists
      ? 'UPDATE MODE: an index already exists in .masterx. The existing index.md, the existing ' +
        'feature pages and the pending change record from the previous execution are provided. ' +
        'Update the index so it stays accurate: apply the recorded changes to the affected ' +
        'features and file registry entries, add features for new capabilities, drop entries for ' +
        'deleted files, and keep unchanged entries stable.\n\n' +
        `EXISTING .masterx/index.md:\n${existing.indexMd || '(empty)'}\n\n` +
        `EXISTING .masterx/docs/*.md:\n${existing.featureDocs || '(none)'}\n\n` +
        `PENDING CHANGES (to incorporate now):\n${existing.changesMd.trim() || '(none recorded)'}\n\n`
      : 'CREATE MODE: no index exists in .masterx yet — generate the full two-tier index from ' +
        'the scan below.\n\n';

    const prompt =
      `USER GOAL (context for what the planner will later implement):\n${goal.trim() || '(no specific goal yet — summarize the codebase)'}\n\n` +
      `WORKSPACE FILE LIST (${truncatedList.length} shown of ${fileList.length} total):\n${listBlock}\n\n` +
      updateBlock +
      `SAMPLED FILE CONTENTS (truncated to ${SAMPLE_CONTENT_CAP} chars):\n${sampleBlock}\n\n` +
      'Produce the JSON with `summary` and `index` now.';

    const outcome = await runClaudeCli({
      cliPath: this.cliPath,
      cwd: this.cwd,
      model: this.model,
      settingsPath: this.settingsPath,
      role: 'worker',
      prompt,
      system,
      tools: INDEX_TOOLS,
      allowedTools: INDEX_TOOLS,
      permissionMode: 'dontAsk',
      timeoutMs: 10 * 60 * 1000,
      signal: this.signal,
      jsonSchema: INDEX_SCHEMA,
      log: this.log,
    });

    this.logFor(outcome);
    return parseIndexResult(outcome.result);
  }

  /**
   * Stage 3: produce the deliverable for one Master-specified SubTask —
   * complete file contents for file actions, or the exact command line for
   * run_command actions.
   */
  async executeTask(task: SubTask, existingContent?: string): Promise<string> {
    if (task.action === 'run_command') {
      return this.draftCommand(task);
    }
    return this.draftFile(task, existingContent);
  }

  /** Draft a single shell command line from the Master's instructions. */
  private async draftCommand(task: SubTask): Promise<string> {
    const targetShell = process.platform === 'win32' ? 'cmd.exe' : 'bash';
    const syntaxHint =
      process.platform === 'win32'
        ? 'Use cmd.exe syntax only — no PowerShell, no bash, no POSIX sh. Prefer `where` over `which`, `dir` over `ls`. One simple command is best.'
        : 'Use POSIX bash syntax only.';

    const system =
      'You are the executing Worker in a Master-Worker code-generation pipeline. ' +
      `You receive one instruction from the planning model and must return EXACTLY ONE ${targetShell} ` +
      'command line to run in the project workspace. ' +
      `${syntaxHint} ` +
      'Respond with the command line only: no markdown fences, no commentary, no surrounding quotes. ' +
      'The command must be non-interactive and safe to run unattended.';

    const prompt =
      `COMMAND LABEL: ${task.targetPath}\n\n` +
      `MASTER INSTRUCTIONS:\n${task.instructions.trim()}\n\n` +
      'Return the single command line now.';

    const outcome = await runClaudeCli({
      cliPath: this.cliPath,
      cwd: this.cwd,
      model: this.model,
      settingsPath: this.settingsPath,
      role: 'worker',
      prompt,
      system,
      tools: DRAFT_TOOLS,
      allowedTools: [],
      timeoutMs: 5 * 60 * 1000,
      signal: this.signal,
      log: this.log,
    });

    this.logFor(outcome);

    const command = stripWrappingFences(outcome.result).trim();
    if (!command) {
      throw new ClaudeCliError(`Worker returned an empty command for task ${task.id}.`);
    }
    // Collapse to one line: the Master asked for a single command line.
    return command.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).join(' && ');
  }

  /** Draft complete file contents from the Master's instructions. */
  private async draftFile(task: SubTask, existingContent?: string): Promise<string> {
    const isCreate = task.action === 'create_file';
    const system =
      'You are the executing Worker in a Master-Worker code-generation pipeline. ' +
      'You receive one file task from the planning model and must return the COMPLETE contents ' +
      'of the file to write — a full, working implementation with proper error handling and no ' +
      'placeholders, stubs, or "TODO: implement" sections. ' +
      'When editing an existing file you are given its current contents: return the entire updated ' +
      'file with the requested changes applied and everything else preserved — never a diff, never ' +
      'only the changed lines. ' +
      'Respond with the raw file contents ONLY: no markdown fences, no explanations before or after. ' +
      'If the instructions specify a language or style, follow it exactly.';

    const existingBlock =
      existingContent !== undefined && existingContent.length > 0
        ? `\n\nCURRENT FILE CONTENTS:\n${existingContent.slice(0, EXISTING_CONTENT_CAP)}${
            existingContent.length > EXISTING_CONTENT_CAP ? '\n… [truncated]' : ''
          }`
        : existingContent !== undefined
          ? '\n\nCURRENT FILE CONTENTS:\n(empty file)'
          : '';

    const prompt =
      `ACTION: ${isCreate ? 'CREATE a new file' : 'EDIT an existing file'}\n` +
      `TARGET PATH: ${task.targetPath}\n\n` +
      `MASTER INSTRUCTIONS:\n${task.instructions.trim()}${existingBlock}\n\n` +
      'Return the complete file contents now.';

    const outcome = await runClaudeCli({
      cliPath: this.cliPath,
      cwd: this.cwd,
      model: this.model,
      settingsPath: this.settingsPath,
      role: 'worker',
      prompt,
      system,
      tools: DRAFT_TOOLS,
      allowedTools: [],
      timeoutMs: 10 * 60 * 1000,
      signal: this.signal,
      log: this.log,
    });

    this.logFor(outcome);

    const contents = stripWrappingFences(outcome.result);
    if (!contents.trim()) {
      throw new ClaudeCliError(
        `Worker returned empty file contents for task ${task.id} (${task.targetPath}).`
      );
    }
    return contents;
  }

  private logFor(outcome: ClaudeCliResult): void {
    this.log(
      `Worker finished: ${outcome.output_tokens} output tokens, ` +
        `$${outcome.total_cost_usd.toFixed(4)}, ${Math.round(outcome.durationMs / 1000)}s.`,
      'debug'
    );
  }
}

/** Re-exported so the orchestrator can path-normalize task targets uniformly. */
export function toPosixRelative(root: string, target: string): string {
  return path.relative(root, target).replace(/\\/g, '/');
}

/** Parse and normalize the Worker's index JSON into strict one-line entries. */
function parseIndexResult(result: string): { summary: string; index: IndexArtifacts } {
  const parsed = parseJsonResult(result, 'Worker index') as {
    summary?: unknown;
    index?: { hld?: unknown; features?: unknown };
  };

  const summary = typeof parsed.summary === 'string' ? parsed.summary.trim() : '';
  const hld = typeof parsed.index?.hld === 'string' ? parsed.index.hld.trim() : '';
  const rawFeatures = Array.isArray(parsed.index?.features) ? parsed.index!.features : [];

  const features: IndexArtifacts['features'] = [];
  for (const raw of rawFeatures) {
    const f = raw as { name?: unknown; slug?: unknown; lld?: unknown; files?: unknown };
    const name = typeof f.name === 'string' ? f.name.trim() : '';
    if (!name) {
      continue;
    }

    const files: IndexArtifacts['features'][number]['files'] = [];
    if (Array.isArray(f.files)) {
      for (const rawFile of f.files) {
        const file = rawFile as { path?: unknown; description?: unknown };
        const filePath = typeof file.path === 'string' ? file.path.trim().replace(/`/g, '') : '';
        // Strict one-line description: collapse any stray newlines/spacing.
        const description =
          typeof file.description === 'string' ? file.description.replace(/\s+/g, ' ').trim() : '';
        if (filePath && description) {
          files.push({ path: filePath, description });
        }
      }
    }

    features.push({
      name,
      slug: slugify(typeof f.slug === 'string' && f.slug.trim() ? f.slug : name),
      lld: typeof f.lld === 'string' ? f.lld.trim() : '',
      files,
    });
  }

  if (!summary) {
    throw new ClaudeCliError('Worker returned an empty architectural summary.');
  }
  if (!hld && features.length === 0) {
    throw new ClaudeCliError('Worker returned an empty hierarchical index.');
  }

  return { summary, index: { hld, features } };
}

/** Re-exported for callers that need to validate structured Worker output. */
export { parseJsonResult, truncate };
