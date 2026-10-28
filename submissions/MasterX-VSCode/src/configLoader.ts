import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { resolveClaudeCliPath } from './claudeCli';
import { ConfigLoadResult, MasterXConfig, ResolvedModel } from './types';

/**
 * Fallback Master model when nothing is configured. Only used when neither the
 * VS Code settings, the environment, nor ~/.claude/settings.json resolve one.
 */
export const FALLBACK_MASTER_MODEL = 'claude-opus-5-5';

/** Fallback Worker model when nothing is configured. */
export const FALLBACK_WORKER_MODEL = 'claude-haiku-5-5';

/** Default endpoint that lists the selectable models (OpenAI-compatible). */
export const DEFAULT_MODEL_LIST_URL = 'https://creditclaim.reskilll.com/llm/v1/models';

/** Minimal shape of ~/.claude/settings.json that MasterX understands. */
interface ClaudeCliSettings {
  model?: string;
  env?: Record<string, string | undefined>;
}

/** Alias → concrete model id, mirroring the Claude CLI's alias table. */
const MODEL_ALIASES: Record<string, string> = {
  opus: 'claude-opus-5-5',
  sonnet: 'claude-sonnet-5-5',
  haiku: 'claude-haiku-5-5',
  fable: 'claude-fable-5-1',
};

/**
 * Expand a leading `~` to the user home directory (Windows and POSIX).
 */
export function expandHome(p: string): string {
  if (!p) {
    return p;
  }
  if (p === '~') {
    return os.homedir();
  }
  const normalized = p.replace(/\\/g, '/');
  if (normalized.startsWith('~/')) {
    return path.join(os.homedir(), p.slice(2));
  }
  return p;
}

/**
 * Location of the Claude CLI settings file. Mirrors `~/.claude/settings.json`.
 */
export function claudeSettingsPath(): string {
  return path.join(os.homedir(), '.claude', 'settings.json');
}

/**
 * Read and parse `~/.claude/settings.json`. Returns undefined when the file is
 * absent, and throws a descriptive error when it exists but is not valid JSON.
 */
export function readClaudeCliSettings(): { settings: ClaudeCliSettings; path: string } | undefined {
  const settingsFile = claudeSettingsPath();
  if (!fs.existsSync(settingsFile)) {
    return undefined;
  }
  const raw = fs.readFileSync(settingsFile, 'utf8');
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { settings: {}, path: settingsFile };
    }
    return { settings: parsed as ClaudeCliSettings, path: settingsFile };
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to parse Claude CLI settings at ${settingsFile}: ${detail}`);
  }
}

function looksLikeAlias(value: string): boolean {
  return Object.prototype.hasOwnProperty.call(MODEL_ALIASES, value.trim().toLowerCase());
}

/**
 * Resolve a model value that may be an alias (`opus`, `sonnet`, `haiku`,
 * `fable`) the way the Claude CLI does: check `ANTHROPIC_DEFAULT_<ALIAS>_MODEL`
 * first, then `ANTHROPIC_MODEL`, then fall back to the known concrete id.
 *
 * Aliases are expanded so the panel status bar shows a real model id; the
 * alias itself is also accepted by `claude --model`.
 */
function resolveAlias(value: string, cliEnv: Record<string, string | undefined>): string {
  const trimmed = value.trim();
  const lower = trimmed.toLowerCase();
  const alias = lower.startsWith('claude-') ? lower.split('-')[1] : lower;

  const defaultEnvKey = `ANTHROPIC_DEFAULT_${(alias || lower).toUpperCase()}_MODEL`;
  const fromDefault = cliEnv[defaultEnvKey] ?? process.env[defaultEnvKey];
  if (fromDefault && fromDefault.trim()) {
    return fromDefault.trim();
  }

  const fromModel = cliEnv.ANTHROPIC_MODEL ?? process.env.ANTHROPIC_MODEL;
  if (fromModel && fromModel.trim()) {
    return fromModel.trim();
  }

  return MODEL_ALIASES[alias ?? lower] ?? trimmed;
}

/** Turn a raw configured value into a ResolvedModel, expanding aliases. */
function toResolved(
  value: string,
  source: string,
  cliEnv: Record<string, string | undefined>
): ResolvedModel {
  const trimmed = value.trim();
  if (!trimmed) {
    return { model: '', modelSource: source };
  }
  if (looksLikeAlias(trimmed)) {
    return {
      model: resolveAlias(trimmed, cliEnv),
      modelSource: `${source} (alias "${trimmed}")`,
    };
  }
  return { model: trimmed, modelSource: source };
}

/** A resolved candidate plus a label naming where it actually came from. */
interface SourcedValue {
  value: string;
  source: string;
}

/**
 * Returns the first non-empty candidate along with a label naming where the
 * value actually came from, so the status bar and config panel never claim a
 * setting came from the wrong place.
 */
function firstSourced(...candidates: Array<{ value: string | undefined; source: string }>): SourcedValue | undefined {
  for (const candidate of candidates) {
    if (candidate.value !== undefined && candidate.value.trim() !== '') {
      return { value: candidate.value.trim(), source: candidate.source };
    }
  }
  return undefined;
}

/**
 * Load all MasterX configuration by merging (highest precedence first):
 *   1. VS Code workspace/user settings (`masterx.*`)
 *   2. Environment variables (ANTHROPIC_*, CLAUDE_CODE_SUBAGENT_MODEL)
 *   3. `~/.claude/settings.json` (when `masterx.useClaudeCliConfig` is true)
 *
 * Master and Worker are two separate `claude` CLI instances with different
 * model ids. Authentication is the CLI's own concern — MasterX never reads or
 * stores credentials.
 */
export function loadConfig(): ConfigLoadResult {
  const warnings: string[] = [];
  const cfg = vscode.workspace.getConfiguration('masterx');

  const useClaudeCliConfig = cfg.get<boolean>('useClaudeCliConfig') ?? true;

  let cli: { settings: ClaudeCliSettings; path: string } | undefined;
  if (useClaudeCliConfig) {
    try {
      cli = readClaudeCliSettings();
      if (!cli) {
        warnings.push(
          `Claude CLI settings not found at ${claudeSettingsPath()}. Falling back to VS Code settings and environment variables.`
        );
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      warnings.push(detail);
    }
  }

  const cliEnv = cli?.settings.env ?? {};
  const cliPathLabel = cli ? cli.path : claudeSettingsPath();

  // ---- OpenAI API key (model catalog + run authentication) ----------------
  // Precedence: masterx.openAiApiKey → OPENAI_API_KEY → ANTHROPIC_AUTH_TOKEN.
  //
  // The last leg exists because the default catalog endpoint is the same
  // gateway the Claude CLI talks to, so the CLI's own bearer token is normally
  // the one that lists its models. It is only reached when no explicit key is
  // configured, and `firstSourced` reports which one was used so nothing is
  // picked up silently.
  const openAiApiKey =
    firstSourced(
      { value: cfg.get<string>('openAiApiKey'), source: 'masterx.openAiApiKey setting' },
      { value: process.env.OPENAI_API_KEY, source: 'OPENAI_API_KEY environment variable' },
      {
        value: cliEnv.ANTHROPIC_AUTH_TOKEN,
        source: `${cliPathLabel} → env.ANTHROPIC_AUTH_TOKEN`,
      },
      { value: process.env.ANTHROPIC_AUTH_TOKEN, source: 'ANTHROPIC_AUTH_TOKEN environment variable' }
    )?.value ?? '';

  // ---- Model catalog endpoint --------------------------------------------
  const modelListUrl =
    cfg.get<string>('modelListUrl')?.trim() || DEFAULT_MODEL_LIST_URL;

  // Advisory only: without the key the dropdown falls back to manual entry and
  // the CLI run inherits credentials from ~/.claude/settings.json.
  if (!openAiApiKey) {
    warnings.push(
      'No API key resolved for the model catalog — the dropdown cannot fetch the model list and ' +
        'will ask for a model id by hand. Set `masterx.openAiApiKey`, or OPENAI_API_KEY / ' +
        'ANTHROPIC_AUTH_TOKEN in the environment or ~/.claude/settings.json.'
    );
  }

  // ---- Claude CLI binary -------------------------------------------------
  let claudeCliPath = '';
  try {
    claudeCliPath = resolveClaudeCliPath(expandHome(cfg.get<string>('claudeCliPath') ?? ''));
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    warnings.push(detail);
  }

  // ---- Master model (deep reasoning) -------------------------------------
  // Precedence: masterx.masterModel → masterx.anthropicModel (legacy alias for
  // the same setting) → ~/.claude/settings.json `model` → ANTHROPIC_MODEL → fallback.
  const explicitMaster = firstSourced(
    { value: cfg.get<string>('masterModel'), source: 'masterx.masterModel setting' },
    { value: cfg.get<string>('anthropicModel'), source: 'masterx.anthropicModel setting' }
  );
  let master: ResolvedModel;
  if (explicitMaster) {
    master = toResolved(explicitMaster.value, explicitMaster.source, cliEnv);
  } else if (cli?.settings.model && cli.settings.model.trim()) {
    master = toResolved(cli.settings.model, `${cliPathLabel} → "model"`, cliEnv);
  } else {
    const fromEnv = firstSourced(
      { value: cliEnv.ANTHROPIC_MODEL, source: `${cliPathLabel} → env.ANTHROPIC_MODEL` },
      { value: process.env.ANTHROPIC_MODEL, source: 'ANTHROPIC_MODEL environment variable' }
    );
    master = fromEnv
      ? toResolved(fromEnv.value, fromEnv.source, cliEnv)
      : { model: FALLBACK_MASTER_MODEL, modelSource: 'built-in fallback' };
  }

  // ---- Worker model (indexing + drafting) --------------------------------
  // Precedence: masterx.workerModel → CLAUDE_CODE_SUBAGENT_MODEL (the model the
  // Claude CLI itself hands to subagents) → ANTHROPIC_DEFAULT_HAIKU_MODEL → fallback.
  // Never equal to the Master: the whole point is a cheaper second model.
  const explicitWorker = firstSourced({
    value: cfg.get<string>('workerModel'),
    source: 'masterx.workerModel setting',
  });
  let worker: ResolvedModel;
  if (explicitWorker) {
    worker = toResolved(explicitWorker.value, explicitWorker.source, cliEnv);
  } else {
    const candidate = firstSourced(
      {
        value: cliEnv.CLAUDE_CODE_SUBAGENT_MODEL,
        source: `${cliPathLabel} → env.CLAUDE_CODE_SUBAGENT_MODEL`,
      },
      {
        value: process.env.CLAUDE_CODE_SUBAGENT_MODEL,
        source: 'CLAUDE_CODE_SUBAGENT_MODEL environment variable',
      },
      {
        value: cliEnv.ANTHROPIC_DEFAULT_HAIKU_MODEL,
        source: `${cliPathLabel} → env.ANTHROPIC_DEFAULT_HAIKU_MODEL`,
      },
      {
        value: process.env.ANTHROPIC_DEFAULT_HAIKU_MODEL,
        source: 'ANTHROPIC_DEFAULT_HAIKU_MODEL environment variable',
      }
    );
    worker = candidate
      ? toResolved(candidate.value, candidate.source, cliEnv)
      : { model: FALLBACK_WORKER_MODEL, modelSource: 'built-in fallback' };
  }

  return {
    config: {
      claudeCliPath,
      master,
      worker,
      openAiApiKey,
      modelListUrl,
    },
    warnings,
  };
}

/**
 * Validate that the CLI and both model ids resolved. Returns a list of
 * human-readable problems; empty means the config is usable.
 */
export function validateConfig(config: MasterXConfig): string[] {
  const problems: string[] = [];
  const { claudeCliPath, master, worker } = config;

  if (!claudeCliPath) {
    problems.push(
      'Claude CLI: not found. Install it with `npm install -g @anthropic-ai/claude-code`, ' +
        'or set `masterx.claudeCliPath` to the absolute path of the `claude` executable.'
    );
  }

  if (!master.model) {
    problems.push(
      'Master: no model resolved. Set `masterx.masterModel`, or a `model` entry in ~/.claude/settings.json.'
    );
  }

  if (!worker.model) {
    problems.push(
      'Worker: no model resolved. Set `masterx.workerModel`, or configure CLAUDE_CODE_SUBAGENT_MODEL in ~/.claude/settings.json.'
    );
  }

  return problems;
}

/**
 * Mask a secret for display (kept for the config panel; MasterX itself no
 * longer reads credentials).
 */
export function maskSecret(secret: string | undefined): string {
  if (!secret) {
    return '(not set)';
  }
  const trimmed = secret.trim();
  if (trimmed.length <= 8) {
    return '••••••••';
  }
  return `${trimmed.slice(0, 4)}…${trimmed.slice(-4)} (${trimmed.length} chars)`;
}
