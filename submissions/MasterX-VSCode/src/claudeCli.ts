import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { LogFn } from './types';

/** Cap on characters of captured stdout/stderr per invocation. */
const MAX_CAPTURED_OUTPUT = 4_000_000;

/**
 * Raised for any Claude CLI failure (missing binary, non-zero exit, unusable
 * or empty output).
 */
export class ClaudeCliError extends Error {
  constructor(
    message: string,
    /** Exit code of the CLI process, when one was observed. */
    public readonly exitCode?: number,
    /** Tail of stderr, for context. */
    public readonly stderrTail?: string,
    public override readonly cause?: unknown
  ) {
    super(message);
    this.name = 'ClaudeCliError';
  }
}

export type CliRole = 'master' | 'worker';

export interface ClaudeCliRunOptions {
  /** Resolved path to the `claude` executable. */
  cliPath: string;
  /** Workspace directory the CLI runs in (also its permission root). */
  cwd: string;
  /** Model id or alias to pass to `--model`. */
  model: string;
  /** Role label used in logs and error messages. */
  role: CliRole;
  /** User prompt. */
  prompt: string;
  /** System prompt (`--system-prompt`). */
  system?: string;
  /** Built-in tools to expose. Pass [] to disable all tools. */
  tools?: string[];
  /** Allowed tools (permissions) applied on top of `tools`. */
  allowedTools?: string[];
  /** Permission mode for the session. */
  permissionMode?: string;
  /**
   * Run-scoped settings.json merged over ~/.claude/settings.json. Carries the
   * model ids chosen in the dropdowns and the OpenAI API key for the run.
   */
  settingsPath?: string;
  /** When set, `--json-schema` is passed and the parsed result is validated. */
  jsonSchema?: Record<string, unknown>;
  /** Milliseconds before the CLI is killed (default 15 minutes). */
  timeoutMs?: number;
  /** Aborting this signal kills the CLI process and raises a "stopped" error. */
  signal?: AbortSignal;
  log?: LogFn;
}

export interface ClaudeCliResult {
  /** The `result` field from `--output-format json`. */
  result: string;
  /** `subtype` from the CLI (`success`, `error_during_execution`, …). */
  subtype: string;
  is_error: boolean;
  num_turns: number;
  total_cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  /** Duration of the whole run in milliseconds. */
  durationMs: number;
}

interface CliResultEnvelope {
  type?: string;
  subtype?: string;
  is_error?: boolean;
  result?: string;
  num_turns?: number;
  total_cost_usd?: number;
  duration_ms?: number;
  usage?: { input_tokens?: number; output_tokens?: number };
  error?: string | { message?: string };
}

/**
 * Locate the `claude` executable. Honours `masterx.claudeCliPath` (passed in),
 * then `CLAUDE_CLI_PATH`, then `claude` / `claude.cmd` on PATH.
 */
export function resolveClaudeCliPath(configured?: string): string {
  const candidates: string[] = [];
  if (configured && configured.trim()) {
    candidates.push(configured.trim());
  }
  const fromEnv = process.env.CLAUDE_CLI_PATH;
  if (fromEnv && fromEnv.trim()) {
    candidates.push(fromEnv.trim());
  }
  candidates.push('claude');

  for (const candidate of candidates) {
    if (candidate === 'claude') {
      const resolved = findOnPath('claude');
      if (resolved) {
        return resolved;
      }
      continue;
    }
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new ClaudeCliError(
    'Claude CLI not found. Install it (`npm install -g @anthropic-ai/claude-code`), ensure `claude` is on PATH, ' +
      'or set `masterx.claudeCliPath` to the absolute path of the executable.'
  );
}

/** Run one non-interactive `claude -p` invocation and return the parsed envelope. */
export async function runClaudeCli(options: ClaudeCliRunOptions): Promise<ClaudeCliResult> {
  const log = options.log ?? (() => undefined);
  const cliPath = options.cliPath;
  const timeoutMs = options.timeoutMs ?? 15 * 60 * 1000;
  const roleLabel = options.role === 'master' ? 'Master' : 'Worker';

  if (!fs.existsSync(cliPath)) {
    throw new ClaudeCliError(
      `${roleLabel}: Claude CLI not found at "${cliPath}". Check \`masterx.claudeCliPath\`.`
    );
  }

  const args = buildArgs(options);
  log(`${roleLabel}: claude CLI → ${options.model}`, 'debug');

  let stdout = '';
  let stderr = '';
  let captured = 0;

  const signal = options.signal;
  if (signal?.aborted) {
    throw new ClaudeCliError(`${roleLabel}: run stopped by user.`);
  }

  const exit = await new Promise<number>((resolve, reject) => {
    const child = spawn(cliPath, args, {
      cwd: options.cwd,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
      // shell:false — the executable is a real .exe, never a shell script.
    });

    // The prompt is delivered over stdin rather than as a positional argument:
    // command lines are length-capped (≈32k chars on Windows) and index-update
    // prompts embed the whole existing `.masterx` index. `claude --print` reads
    // the user prompt from stdin when none is passed on the command line.
    child.stdin.on('error', () => {
      // EPIPE when the CLI exits before consuming stdin is harmless here —
      // the exit path below reports the real outcome.
    });
    child.stdin.end(options.prompt);

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');

    child.stdout.on('data', (chunk: string) => {
      if (captured < MAX_CAPTURED_OUTPUT) {
        stdout += chunk;
        captured += chunk.length;
      }
    });
    child.stderr.on('data', (chunk: string) => {
      if (captured < MAX_CAPTURED_OUTPUT) {
        stderr += chunk;
        captured += chunk.length;
      }
    });

    const onAbort = () => {
      child.kill('SIGKILL');
      reject(new ClaudeCliError(`${roleLabel}: run stopped by user.`));
    };
    signal?.addEventListener('abort', onAbort, { once: true });

    const cleanup = () => {
      clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
    };

    const timer = setTimeout(() => {
      cleanup();
      child.kill('SIGKILL');
      reject(
        new ClaudeCliError(
          `${roleLabel}: Claude CLI timed out after ${Math.round(timeoutMs / 60000)} minutes.`
        )
      );
    }, timeoutMs);

    child.on('error', (error) => {
      cleanup();
      reject(new ClaudeCliError(`${roleLabel}: failed to launch Claude CLI: ${error.message}`, undefined, undefined, error));
    });

    child.on('close', (code) => {
      cleanup();
      resolve(code ?? 1);
    });
  });

  // --output-format json prints one result envelope as the final line; any
  // preceding lines are progress chatter, warnings, or parser noise.
  const envelope = pickResultEnvelope(stdout);
  const stderrTail = stderr.trim().slice(-400);

  if (!envelope) {
    throw new ClaudeCliError(
      `${roleLabel}: Claude CLI produced no parseable result output (exit code ${exit}).` +
        (stderrTail ? ` stderr: ${stderrTail}` : '') +
        (stdout.trim() ? ` stdout began with: ${stdout.trim().slice(0, 200)}` : ''),
      exit,
      stderrTail
    );
  }

  if (exit !== 0 || envelope.is_error === true) {
    const detail =
      (typeof envelope.error === 'string' ? envelope.error : envelope.error?.message) ??
      envelope.subtype ??
      `exit code ${exit}`;
    throw new ClaudeCliError(`${roleLabel}: Claude CLI reported a failure: ${detail}`, exit, stderrTail);
  }

  const result = typeof envelope.result === 'string' ? envelope.result : '';

  if (envelope.type !== 'result' && envelope.type !== undefined) {
    throw new ClaudeCliError(
      `${roleLabel}: unexpected Claude CLI message type "${envelope.type}".`,
      exit,
      stderrTail
    );
  }

  if (!result.trim()) {
    throw new ClaudeCliError(
      `${roleLabel}: Claude CLI returned an empty result (subtype: ${envelope.subtype ?? 'unknown'}).`,
      exit,
      stderrTail
    );
  }

  // `--json-schema` promises structured output; hold the model to it.
  if (options.jsonSchema) {
    parseJsonResult(result, roleLabel);
  }

  return {
    result,
    subtype: envelope.subtype ?? 'unknown',
    is_error: envelope.is_error ?? false,
    num_turns: envelope.num_turns ?? 0,
    total_cost_usd: envelope.total_cost_usd ?? 0,
    input_tokens: envelope.usage?.input_tokens ?? 0,
    output_tokens: envelope.usage?.output_tokens ?? 0,
    durationMs: envelope.duration_ms ?? 0,
  };
}

/** Build the `claude` argument vector for one run. */
export function buildArgs(options: ClaudeCliRunOptions): string[] {
  const args: string[] = [
    '--print',
    '--output-format', 'json',
    '--model', options.model,
    // Each MasterX invocation is a one-shot; never stitch onto old sessions
    // and never leave transcript clutter behind.
    '--no-session-persistence',
  ];

  // Run-scoped settings: the model ids and the OpenAI API key selected in the
  // MasterX UI, merged over ~/.claude/settings.json by the CLI itself.
  if (options.settingsPath && options.settingsPath.trim()) {
    args.push('--settings', options.settingsPath.trim());
  }

  if (options.system) {
    args.push('--system-prompt', options.system);
  }

  // Pin the tool surface. A tight allow-list keeps the CLI cheap and on-task:
  // the Worker drafts, the Master reasons — neither should drive the shell.
  // An empty list disables every tool. Note this must be a real empty argument,
  // not the two-character string `""` — that is what a shell would unwrap for
  // us, and `spawn` passes arguments verbatim.
  const tools = options.tools ?? ['Read', 'Glob', 'Grep'];
  args.push('--tools', tools.length > 0 ? tools.join(',') : '');

  const allowed = options.allowedTools ?? tools;
  if (allowed.length > 0) {
    args.push('--allowedTools', allowed.join(','));
  }

  if (options.permissionMode) {
    args.push('--permission-mode', options.permissionMode);
  }

  if (options.jsonSchema) {
    args.push('--json-schema', JSON.stringify(options.jsonSchema));
  }

  // The prompt itself is intentionally absent from the command line: it is
  // written to the child's stdin (see runClaudeCli). Command lines are capped
  // (≈32k chars on Windows) and index prompts routinely exceed that.
  return args;
}

/**
 * Parse the CLI's JSON output, tolerating preamble lines before the envelope.
 */
export function pickResultEnvelope(stdout: string): CliResultEnvelope | undefined {
  const lines = stdout.split(/\r?\n/);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (!line) {
      continue;
    }
    try {
      const parsed = JSON.parse(line) as CliResultEnvelope;
      if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      // Not the result line — keep walking backwards.
    }
  }
  return undefined;
}

/**
 * Parse the `result` string as JSON and throw a typed error when it is not.
 */
export function parseJsonResult(result: string, label: string): unknown {
  const stripped = stripWrappingFences(result);
  try {
    return JSON.parse(stripped);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new ClaudeCliError(
      `${label}: expected structured JSON but got unparseable output (${detail}). ` +
        `Output began with: ${stripped.slice(0, 200)}`
    );
  }
}

/**
 * Remove a single layer of wrapping markdown code fences the model sometimes
 * adds despite being told not to. Keeps the inner text intact.
 */
export function stripWrappingFences(text: string): string {
  const trimmed = text.trim();
  const fenceMatch = trimmed.match(/^```[a-zA-Z0-9_+-]*\r?\n([\s\S]*?)\r?\n```$/);
  if (fenceMatch) {
    return fenceMatch[1];
  }
  return text;
}

/** Truncate text for log/plan payloads. */
export function truncate(text: string, max: number): string {
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, max)}… [truncated ${text.length - max} chars]`;
}

/** Look up an executable on PATH (PATHEXT-aware on Windows). */
function findOnPath(name: string): string | undefined {
  const pathEnv = process.env.PATH ?? process.env.Path ?? '';
  const dirs = pathEnv.split(path.delimiter).filter(Boolean);
  const exts =
    process.platform === 'win32'
      ? (process.env.PATHEXT ?? '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean)
      : [''];

  for (const dir of dirs) {
    for (const ext of exts) {
      const candidate = `${dir.replace(/[\\/]+$/, '')}${path.sep}${name}${ext.toLowerCase()}`;
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }
    // Also try the bare name in case it already carries an extension.
    const bare = `${dir.replace(/[\\/]+$/, '')}${path.sep}${name}`;
    if (fs.existsSync(bare)) {
      return bare;
    }
  }
  return undefined;
}
