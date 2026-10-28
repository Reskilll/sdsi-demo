/**
 * Run-scoped settings.json.
 *
 * MasterX drives `claude` CLI instances with `--settings <file>`, pointing each
 * run at a small settings file that carries the model ids chosen in the MasterX
 * dropdowns and the OpenAI API key from MasterX settings. The CLI merges that
 * file over `~/.claude/settings.json` key-wise (verified), so only the keys
 * MasterX overrides need to be present here.
 *
 * Nothing is written back to the user's global ~/.claude/settings.json — that
 * file is left untouched, and the run file is deleted when the run finishes.
 */
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export interface RunSettingsOptions {
  /** Master model id chosen in the dropdown. */
  masterModel: string;
  /** Worker model id chosen in the dropdown. */
  workerModel: string;
  /**
   * OpenAI API key from `masterx.openAiApiKey`. Written into the run settings
   * as the bearer token the CLI authenticates with. Omit to inherit whatever
   * ~/.claude/settings.json already provides.
   */
  openAiApiKey?: string;
  /** Optional base URL override; omitted to inherit. */
  baseUrl?: string;
}

export interface RunSettingsFile {
  /** Absolute path to the generated settings file, to pass as `--settings`. */
  path: string;
  /** Keys written into the file, for logging (never values). */
  keys: string[];
}

/**
 * Write the run-scoped settings file and return its path.
 *
 * The file contains only overrides — the CLI merges it over the global config,
 * so base URL and anything else already configured there still apply.
 */
export function writeRunSettings(options: RunSettingsOptions): RunSettingsFile {
  const env: Record<string, string> = {};
  const keys: string[] = [];

  // Model selection: the CLI's own `model` key plus the env keys that feed its
  // role resolution, so a `claude` invocation without an explicit --model still
  // lands on the selected id.
  const root: Record<string, unknown> = {};

  if (options.masterModel.trim()) {
    root.model = options.masterModel.trim();
    keys.push('model');
  }
  if (options.workerModel.trim()) {
    env.CLAUDE_CODE_SUBAGENT_MODEL = options.workerModel.trim();
    keys.push('env.CLAUDE_CODE_SUBAGENT_MODEL');
  }

  // The OpenAI API key is what the run authenticates with. It is passed as the
  // bearer token; ANTHROPIC_API_KEY is explicitly blanked so an empty inherited
  // value cannot shadow it.
  const apiKey = (options.openAiApiKey ?? '').trim();
  if (apiKey) {
    env.ANTHROPIC_AUTH_TOKEN = apiKey;
    keys.push('env.ANTHROPIC_AUTH_TOKEN');
    env.ANTHROPIC_API_KEY = '';
    keys.push('env.ANTHROPIC_API_KEY');
  }

  const baseUrl = (options.baseUrl ?? '').trim();
  if (baseUrl) {
    env.ANTHROPIC_BASE_URL = baseUrl;
    keys.push('env.ANTHROPIC_BASE_URL');
  }

  if (Object.keys(env).length > 0) {
    root.env = env;
  }

  const contents = JSON.stringify(root, null, 2) + '\n';

  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const filePath = path.join(os.tmpdir(), `masterx-run-settings-${stamp}.json`);

  // Restrictive mode is a no-op on Windows but correct on POSIX.
  fs.writeFileSync(filePath, contents, { encoding: 'utf8', mode: 0o600 });

  return { path: filePath, keys };
}

/**
 * Best-effort cleanup of a generated run settings file.
 */
export function disposeRunSettings(filePath: string | undefined): void {
  if (!filePath) {
    return;
  }
  try {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  } catch {
    // Leaving a temp settings file behind is harmless; never fail the run for it.
  }
}

/**
 * Preview of what would be written, for the config panel. Values are masked.
 */
export function describeRunSettings(options: RunSettingsOptions): string[] {
  const lines: string[] = [];
  lines.push(`model                          = ${options.masterModel || '(inherit)'}`);
  lines.push(`env.CLAUDE_CODE_SUBAGENT_MODEL = ${options.workerModel || '(inherit)'}`);
  const apiKey = (options.openAiApiKey ?? '').trim();
  lines.push(
    `env.ANTHROPIC_AUTH_TOKEN       = ${
      apiKey ? `${apiKey.slice(0, 4)}…${apiKey.slice(-4)} (${apiKey.length} chars)` : '(inherit)'
    }`
  );
  lines.push(`env.ANTHROPIC_BASE_URL         = ${options.baseUrl?.trim() || '(inherit)'}`);
  return lines;
}
