import * as path from 'path';
import * as vscode from 'vscode';
import { claudeSettingsPath, loadConfig, validateConfig } from './configLoader';
import { ModelCatalogError, ModelInfo, fetchModelList, preferChatModels } from './modelCatalog';
import { Orchestrator } from './orchestrator';
import { Master } from './master';
import { Worker } from './worker';
import { describeRunSettings, disposeRunSettings, writeRunSettings } from './runSettings';
import {
  LogLevel,
  StageId,
  WebviewInboundMessage,
  WebviewOutboundMessage,
} from './types';

/** Which role a model dropdown is choosing for. */
type ModelRole = 'master' | 'worker';

/** Models chosen when the user picks the static "Auto" entry in the dropdowns. */
const AUTO_MODELS: Record<ModelRole, string> = {
  master: 'anthropic/claude-sonnet-5.5',
  worker: 'xiaomi/mimo-v2.6-pro',
};

/** Resolve a dropdown selection to the model id actually used for a run. */
function resolveModelId(role: ModelRole, model: string): string {
  return model === 'Auto' ? AUTO_MODELS[role] : model;
}

/**
 * The MasterX panel: a self-contained vanilla HTML/CSS/JS webview using only
 * VS Code theme variables. No bundler, no framework.
 *
 * Top:    auto-scrolling console (user goals, run logs, final report)
 * Then:   stage stack — past and current stages, click one for its one-liner
 * Then:   Master / Worker model dropdowns on a single line
 * Bottom: goal chatbox with Execute / Stop / Reset, then the footer
 */
export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'masterx.chatView';

  private view?: vscode.WebviewView;
  private running = false;
  private abortController?: AbortController;
  private catalog?: string[];

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly extensionVersion: string
  ) {}

  // ---------------------------------------------------------------- lifecycle

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, 'media')],
    };
    webviewView.webview.html = this.buildHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(
      async (raw: WebviewInboundMessage) => {
        try {
          await this.handleMessage(raw);
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          this.post({ type: 'log', message: `Internal error: ${message}`, level: 'error' });
          this.post({ type: 'busy', value: false });
          this.post({ type: 'stage', stage: 'error', detail: message });
        }
      },
      undefined
    );

    webviewView.onDidDispose(() => {
      this.view = undefined;
    });
  }

  // ------------------------------------------------------------------- public

  /** Focus the panel and reveal this view. */
  focus(): void {
    void vscode.commands.executeCommand('masterx.chatView.focus');
    this.post({ type: 'focus-input' });
  }

  /** Clear the panel back to its idle state. */
  reset(): void {
    this.post({ type: 'reset' });
    this.postInit();
    this.log('Panel reset.', 'info');
  }

  /** Start a run from the command palette (picks up the current goal text). */
  async executeFromCommand(): Promise<void> {
    if (this.running) {
      this.log('A run is already in progress. Wait for it to finish or press Reset.', 'warn');
      return;
    }
    // The webview owns the goal text; ask it to kick off execution.
    this.post({ type: 'do-execute' });
  }

  /**
   * Open the model dropdown for one role: fetch the catalog, show a QuickPick,
   * and persist the choice into `masterx.masterModel` / `masterx.workerModel`.
   */
  async pickModel(role: ModelRole): Promise<void> {
    const { config, warnings } = loadConfig();
    for (const warning of warnings) {
      this.log(warning, 'warn');
    }

    const title = role === 'master' ? 'Select Master model' : 'Select Worker model';
    const current = role === 'master' ? config.master.model : config.worker.model;
    const settingKey = role === 'master' ? 'masterModel' : 'workerModel';

    let items: vscode.QuickPickItem[] = [];
    let catalogNote = '';

    if (!config.openAiApiKey) {
      catalogNote =
        'No OpenAI API key configured (set `masterx.openAiApiKey`). You can still type a model id below.';
    } else {
      try {
        this.log(`Fetching model list from ${config.modelListUrl}…`, 'debug');
        const catalog = await fetchModelList({
          url: config.modelListUrl,
          apiKey: config.openAiApiKey,
        });
        const models = preferChatModels(catalog);
        items = models.map((m) => this.toQuickPickItem(m, current));
        this.log(`Model catalog: ${models.length} model(s) available.`, 'debug');
      } catch (error) {
        const message =
          error instanceof ModelCatalogError
            ? error.message
            : error instanceof Error
              ? error.message
              : String(error);
        catalogNote = `Could not load the model list: ${message} You can still type a model id below.`;
        this.log(catalogNote, 'warn');
      }
    }

    // Always offer manual entry, and surface the currently selected id first.
    const manualItem: vscode.QuickPickItem = {
      label: '$(edit) Enter a model id…',
      description: 'type it by hand',
      detail: catalogNote || 'Use this when the model is not in the list.',
      alwaysShow: true,
    };

    const currentItems: vscode.QuickPickItem[] =
      current && !items.some((i) => i.label === current)
        ? [
            {
              label: current,
              description: '(currently selected)',
              detail: 'Not present in the catalog — keep using it as-is.',
              alwaysShow: true,
            },
          ]
        : [];

    const quickPick = vscode.window.createQuickPick();
    quickPick.title = title;
    quickPick.placeholder =
      items.length > 0
        ? 'Search models — press Enter to choose, or pick “Enter a model id…”'
        : catalogNote || 'Type a model id';
    quickPick.items = [...currentItems, ...items, manualItem];
    quickPick.matchOnDescription = true;
    quickPick.matchOnDetail = true;

    const picked = await new Promise<vscode.QuickPickItem | undefined>((resolve) => {
      quickPick.onDidAccept(() => {
        resolve(quickPick.selectedItems[0]);
        quickPick.hide();
      });
      quickPick.onDidHide(() => {
        resolve(undefined);
        quickPick.dispose();
      });
      quickPick.show();
    });

    if (!picked) {
      this.log(`No ${role} model selected — keeping "${current}".`, 'info');
      return;
    }

    if (picked === manualItem) {
      await this.promptCustomModel(role);
      return;
    }

    const chosen = picked.label;
    await this.saveModelSetting(settingKey, chosen);
    this.log(`${role === 'master' ? 'Master' : 'Worker'} model set to "${chosen}".`, 'success');
    this.postInit();
  }

  /** Ask for a free-form model id and persist it. */
  private async promptCustomModel(role: ModelRole): Promise<void> {
    const { config } = loadConfig();
    const current = role === 'master' ? config.master.model : config.worker.model;
    const title = role === 'master' ? 'Select Master model' : 'Select Worker model';

    const chosen = await vscode.window.showInputBox({
      title,
      prompt: 'Model id or alias (e.g. `opus`, `sonnet`, `z-ai/glm-5.3-flash`)',
      value: current,
      ignoreFocusOut: true,
      validateInput: (value) =>
        value.trim().length === 0 ? 'Enter a model id' : undefined,
    });

    if (!chosen) {
      this.log(`No ${role} model selected — keeping "${current}".`, 'info');
      this.postInit();
      return;
    }

    const model = chosen.trim();
    await this.saveModelSetting(role === 'master' ? 'masterModel' : 'workerModel', model);
    this.log(`${role === 'master' ? 'Master' : 'Worker'} model set to "${model}".`, 'success');
    this.postInit();
  }

  /** Fetch (once) and post the model catalog for the in-panel dropdowns. */
  private async refreshModels(): Promise<void> {
    const { config } = loadConfig();
    if (!config.openAiApiKey) {
      this.log('Model catalog unavailable: no OpenAI API key configured.', 'debug');
      this.post({ type: 'models', models: [] });
      return;
    }
    try {
      if (!this.catalog) {
        this.log(`Fetching model list from ${config.modelListUrl}…`, 'debug');
        const catalog = await fetchModelList({
          url: config.modelListUrl,
          apiKey: config.openAiApiKey,
        });
        this.catalog = preferChatModels(catalog).map((m) => m.id);
        this.log(`Model catalog: ${this.catalog.length} model(s) available.`, 'debug');
      }
      this.post({ type: 'models', models: this.catalog });
    } catch (error) {
      const message =
        error instanceof ModelCatalogError
          ? error.message
          : error instanceof Error
            ? error.message
            : String(error);
      this.log(`Could not load the model list: ${message}`, 'warn');
      this.post({ type: 'models', models: [] });
    }
  }

  /** Persist a model choice into VS Code user settings. */
  private async saveModelSetting(key: 'masterModel' | 'workerModel', value: string): Promise<void> {
    const cfg = vscode.workspace.getConfiguration('masterx');
    // Workspace wins when a folder is open so a project can pin its own pair;
    // otherwise fall back to user settings.
    const target = vscode.workspace.workspaceFolders?.length
      ? vscode.ConfigurationTarget.Workspace
      : vscode.ConfigurationTarget.Global;
    try {
      await cfg.update(key, value, target);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      this.log(`Could not save masterx.${key}: ${detail}`, 'error');
    }
  }

  /** Map a catalog entry onto a QuickPick row. */
  private toQuickPickItem(model: ModelInfo, current: string): vscode.QuickPickItem {
    const isCurrent = model.id === current;
    return {
      label: model.id,
      description: model.ownedBy ? model.ownedBy : undefined,
      detail: isCurrent ? '(currently selected)' : undefined,
      alwaysShow: isCurrent,
    };
  }

  /** Show the resolved configuration in a readable quick-pick. */
  async showConfig(): Promise<void> {
    const { config, warnings } = loadConfig();
    const problems = validateConfig(config);

    const lines: string[] = [
      'MasterX — Resolved Configuration',
      '',
      `Claude CLI:          ${config.claudeCliPath || '(not found)'}`,
      `CLI settings:        ${claudeSettingsPath()}`,
      '',
      `Master model:        ${config.master.model}`,
      `Master source:       ${config.master.modelSource}`,
      '',
      `Worker model:        ${config.worker.model}`,
      `Worker source:       ${config.worker.modelSource}`,
      '',
      `Model catalog URL:   ${config.modelListUrl}`,
      `OpenAI API key:      ${config.openAiApiKey ? `${config.openAiApiKey.slice(0, 4)}…${config.openAiApiKey.slice(-4)} (${config.openAiApiKey.length} chars)` : '(not set)'}`,
      '',
      'Run-scoped settings.json written for each task run:',
      ...describeRunSettings({
        masterModel: resolveModelId('master', config.master.model),
        workerModel: resolveModelId('worker', config.worker.model),
        openAiApiKey: config.openAiApiKey,
      }).map((line) => `  ${line}`),
      '',
      `Workspace folder:    ${this.workspaceFolderLabel()}`,
      '',
    ];

    if (problems.length > 0) {
      lines.push('Configuration problems:');
      for (const problem of problems) {
        lines.push(`  • ${problem}`);
      }
    } else {
      lines.push('Configuration is complete — ready to run.');
    }
    if (warnings.length > 0) {
      lines.push('');
      lines.push('Warnings:');
      for (const warning of warnings) {
        lines.push(`  • ${warning}`);
      }
    }

    void vscode.window.showInformationMessage(lines.join('\n'), { modal: true, detail: lines.join('\n') });
    this.log('Displayed resolved configuration.', 'info');
  }

  // ---------------------------------------------------------------- messaging

  private async handleMessage(message: WebviewInboundMessage): Promise<void> {
    switch (message?.type) {
      case 'ready':
        this.postInit();
        void this.refreshModels();
        return;

      case 'reset':
        this.post({ type: 'reset' });
        this.postInit();
        return;

      case 'stop':
        if (!this.abortController) {
          this.log('No run in progress.', 'warn');
          return;
        }
        this.abortController.abort();
        this.log('Stop requested — halting the current run…', 'warn');
        return;

      case 'execute': {
        const goal = (message.goal ?? '').trim();
        if (!goal) {
          this.log('Enter a goal before executing.', 'warn');
          return;
        }
        if (this.running) {
          this.log('A run is already in progress.', 'warn');
          return;
        }
        await this.runGoal(goal);
        return;
      }

      case 'set-model': {
        const role: ModelRole = message.role === 'worker' ? 'worker' : 'master';
        const model = (message.model ?? '').trim();
        if (!model) {
          this.log('Model id cannot be empty.', 'warn');
          return;
        }
        await this.saveModelSetting(role === 'master' ? 'masterModel' : 'workerModel', model);
        this.log(`${role === 'master' ? 'Master' : 'Worker'} model set to "${model}".`, 'success');
        this.postInit();
        return;
      }

      case 'custom-model': {
        const role: ModelRole = message.role === 'worker' ? 'worker' : 'master';
        await this.promptCustomModel(role);
        return;
      }

      default:
        this.log(`Unknown message from panel: ${JSON.stringify(message).slice(0, 120)}`, 'warn');
    }
  }

  private post(message: WebviewOutboundMessage): void {
    void this.view?.webview.postMessage(message);
  }

  private log(message: string, level: LogLevel = 'info'): void {
    this.post({ type: 'log', message, level });
  }

  /** Send resolved models + workspace so the status bar can render. */
  private postInit(): void {
    const { config, warnings } = loadConfig();
    const problems = validateConfig(config);

    this.post({
      type: 'init',
      masterModel: config.master.model,
      workerModel: config.worker.model,
    });

    for (const warning of warnings) {
      this.log(warning, 'warn');
    }
    for (const problem of problems) {
      this.log(problem, 'error');
    }
    if (problems.length === 0) {
      this.log(
        `Ready. Master ${config.master.model} · Worker ${config.worker.model}.`,
        'success'
      );
    }
  }

  private workspaceFolderLabel(): string {
    const folder = vscode.workspace.workspaceFolders?.[0];
    return folder ? path.basename(folder.uri.fsPath) : '(no folder open)';
  }

  private requireWorkspaceRootPath(): string {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder) {
      throw new Error('No workspace folder is open. Open a folder before running MasterX.');
    }
    return folder.uri.fsPath;
  }

  // ------------------------------------------------------------------- runner

  private async runGoal(goal: string): Promise<void> {
    const abort = new AbortController();
    this.abortController = abort;
    this.running = true;
    this.post({ type: 'busy', value: true });
    this.post({ type: 'user-input', text: goal });
    this.postInit();

    let runSettingsPath: string | undefined;
    try {
      const { config, warnings } = loadConfig();
      for (const warning of warnings) {
        this.log(warning, 'warn');
      }

      const problems = validateConfig(config);
      if (problems.length > 0) {
        for (const problem of problems) {
          this.log(problem, 'error');
        }
        this.post({ type: 'stage', stage: 'error', detail: problems[0] });
        return;
      }

      const cwd = this.requireWorkspaceRootPath();

      // Run-scoped settings.json: carries the model ids chosen in the dropdowns
      // and the OpenAI API key, merged over ~/.claude/settings.json by the CLI.
      // The global file is never modified; this one is deleted after the run.
      const runSettings = writeRunSettings({
        masterModel: resolveModelId('master', config.master.model),
        workerModel: resolveModelId('worker', config.worker.model),
        openAiApiKey: config.openAiApiKey,
      });
      runSettingsPath = runSettings.path;
      this.log(
        `Run settings: ${path.basename(runSettings.path)} → ${runSettings.keys.join(', ') || '(no overrides)'}`,
        'debug'
      );

      // Two independent `claude` CLI instances with different models: a cheap
      // Worker that indexes and drafts, a deep-thinking Master that plans and
      // reviews.
      const worker = new Worker({
        cliPath: config.claudeCliPath,
        cwd,
        model: resolveModelId('worker', config.worker.model),
        settingsPath: runSettings.path,
        signal: abort.signal,
        log: (message, level) => this.log(message, level),
      });
      const master = new Master({
        cliPath: config.claudeCliPath,
        cwd,
        model: resolveModelId('master', config.master.model),
        settingsPath: runSettings.path,
        signal: abort.signal,
        log: (message, level) => this.log(message, level),
      });

      const orchestrator = new Orchestrator(worker, master, {
        onLog: (message, level) => this.log(message, level),
        onStage: (stage: StageId, detail: string) =>
          this.post({ type: 'stage', stage, detail }),
        onSummary: (text: string) => this.post({ type: 'summary', text }),
      });

      await orchestrator.run(goal, abort.signal);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.log(message, 'error');
      this.post({ type: 'stage', stage: 'error', detail: message });
    } finally {
      disposeRunSettings(runSettingsPath);
      this.abortController = undefined;
      this.running = false;
      this.post({ type: 'busy', value: false });
    }
  }

  // --------------------------------------------------------------------- html

  private buildHtml(webview: vscode.Webview): string {
    const nonce = getNonce();

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MasterX</title>
  <style>
    :root {
      --mx-gap: 8px;
      --mx-radius: 4px;
      --mx-font: var(--vscode-font-family);
      --mx-mono: var(--vscode-editor-font-family, monospace);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 10px;
      font-family: var(--mx-font);
      font-size: calc(var(--vscode-font-size) + 5px);
      color: var(--vscode-foreground);
      background: var(--vscode-panel-background, var(--vscode-sideBar-background));
      display: flex;
      flex-direction: column;
      gap: var(--mx-gap);
      height: 100vh;
      overflow: hidden;
    }

    /* ---------- console ---------- */
    .console-wrap {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      min-height: 0;
    }
    .console-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--vscode-descriptionForeground);
    }
    .console {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 6px;
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border));
      border-radius: var(--mx-radius);
      background: var(--vscode-editor-background);
      font-family: var(--mx-mono);
      font-size: 15px;
      line-height: 1.55;
    }
    .log-line { white-space: pre-wrap; word-break: break-word; }
    .log-line.info    { color: var(--vscode-foreground); }
    .log-line.debug   { color: var(--vscode-descriptionForeground); }
    .log-line.warn    { color: var(--vscode-charts-yellow); }
    .log-line.error   { color: var(--vscode-charts-red); }
    .log-line.success { color: var(--vscode-charts-green); }
    .log-line.user {
      margin: 12px 0 2px;
      padding: 6px 8px;
      font-size: 18px;
      font-weight: 600;
      text-align: right;
      border-right: 3px solid var(--vscode-progressBar-background);
      background: var(--vscode-textBlockQuote-background, rgba(127, 127, 127, 0.08));
      border-radius: 3px;
    }
    .log-line.separator {
      margin: 2px 0 8px;
      color: var(--vscode-descriptionForeground);
      opacity: 0.55;
      white-space: pre;
      overflow: hidden;
    }
    .log-line.stage-banner {
      margin: 14px 0 4px;
      padding-top: 6px;
      border-top: 1px solid var(--vscode-widget-border, var(--vscode-panel-border));
      font-family: var(--mx-font);
      font-size: 15px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--vscode-descriptionForeground);
    }
    .log-line.master {
      margin: 12px 0 2px;
    }
    .log-line.master .entry-label {
      font-size: 18px;
      font-weight: 600;
      color: var(--vscode-charts-green);
    }

    /* ---------- progress tracker (stage stack) ---------- */
    .tracker {
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex-shrink: 0;
      min-height: 0;
      max-height: 30vh;
      overflow-y: auto;
    }
    .stage-empty {
      padding: 4px 6px;
      font-size: 15px;
      color: var(--vscode-descriptionForeground);
    }
    .stage-row {
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border));
      border-radius: var(--mx-radius);
      background: var(--vscode-editor-background);
      flex-shrink: 0;
    }
    .stage-head {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 3px 6px;
      font-size: 16px;
      cursor: pointer;
    }
    .stage-head:hover {
      color: var(--vscode-textLink-foreground);
    }
    .stage-head .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      border: 1.5px solid var(--vscode-descriptionForeground);
      flex-shrink: 0;
    }
    .stage-row.status-running {
      background: var(--vscode-list-activeSelectionBackground);
      color: var(--vscode-list-activeSelectionForeground);
    }
    .stage-row.status-running .dot {
      border-color: var(--vscode-progressBar-background);
      background: var(--vscode-progressBar-background);
      animation: mx-pulse 1.2s ease-in-out infinite;
    }
    .stage-row.status-done .dot {
      border-color: var(--vscode-charts-green);
      background: var(--vscode-charts-green);
    }
    .stage-row.status-failed .dot {
      border-color: var(--vscode-charts-red);
      background: var(--vscode-charts-red);
    }
    .stage-row.status-stopped .dot {
      border-color: var(--vscode-descriptionForeground);
      background: var(--vscode-descriptionForeground);
      opacity: 0.6;
    }
    .stage-title {
      font-weight: 600;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .chevron {
      margin-left: auto;
      flex-shrink: 0;
      font-size: 12px;
      opacity: 0.7;
      transform: rotate(-90deg);
      transition: transform 0.15s ease;
    }
    .stage-row.expanded .chevron {
      transform: rotate(0deg);
    }
    .stage-detail {
      display: none;
      padding: 2px 8px 5px 22px;
      font-size: 15px;
      color: var(--vscode-descriptionForeground);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .stage-row.expanded .stage-detail {
      display: block;
    }
    @keyframes mx-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.45; }
    }

    /* ---------- model selection row ---------- */
    .model-row {
      display: flex;
      gap: 12px;
      flex-shrink: 0;
    }
    .model-cell {
      display: flex;
      align-items: center;
      gap: 6px;
      flex: 1;
      min-width: 0;
    }
    .model-label {
      font-size: 15px;
      color: var(--vscode-descriptionForeground);
      flex-shrink: 0;
    }
    .model-select {
      flex: 1;
      min-width: 0;
      padding: 3px 6px;
      font-family: var(--mx-mono);
      font-size: calc(var(--vscode-font-size) + 5px);
      color: var(--vscode-dropdown-foreground, var(--vscode-foreground));
      background: var(--vscode-dropdown-background, var(--vscode-input-background));
      border: 1px solid var(--vscode-dropdown-border, var(--vscode-widget-border, var(--vscode-panel-border)));
      border-radius: var(--mx-radius);
      outline: none;
    }
    .model-select:focus {
      border-color: var(--vscode-focusBorder);
    }

    /* ---------- chatbox ---------- */
    .input-area {
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex-shrink: 0;
    }
    textarea#goal {
      width: 100%;
      min-height: 48px;
      resize: vertical;
      padding: 6px 8px;
      font-family: var(--mx-font);
      font-size: calc(var(--vscode-font-size) + 5px);
      color: var(--vscode-input-foreground);
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border, transparent);
      border-radius: var(--mx-radius);
      outline: none;
    }
    textarea#goal:focus {
      border-color: var(--vscode-focusBorder);
    }
    .button-row {
      display: flex;
      gap: 6px;
    }
    button {
      flex: 1;
      padding: 5px 10px;
      font-family: var(--mx-font);
      font-size: calc(var(--vscode-font-size) + 5px);
      border: none;
      border-radius: var(--mx-radius);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
    }
    button.primary {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
    }
    button.primary:hover:not(:disabled) { background: var(--vscode-button-hoverBackground); }
    button.primary:disabled {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
      cursor: not-allowed;
    }
    button.secondary {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }
    button.secondary:hover:not(:disabled) {
      background: var(--vscode-button-secondaryHoverBackground);
    }
    button.secondary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .hint {
      font-size: 15px;
      color: var(--vscode-descriptionForeground);
    }

    /* ---------- footer ---------- */
    .footer {
      padding-top: 4px;
      flex-shrink: 0;
      font-size: 15px;
      color: var(--vscode-descriptionForeground);
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="console-wrap">
    <div class="console-head">
      <span>Console</span>
      <span id="logCount">0</span>
    </div>
    <div class="console" id="console"></div>
  </div>

  <div class="tracker" id="tracker">
    <div class="stage-empty" id="stageEmpty">Idle — enter a goal and press Execute</div>
  </div>

  <div class="model-row">
    <div class="model-cell">
      <label class="model-label" for="masterModel">Master</label>
      <select class="model-select" id="masterModel" aria-label="Select Master model"></select>
    </div>
    <div class="model-cell">
      <label class="model-label" for="workerModel">Worker</label>
      <select class="model-select" id="workerModel" aria-label="Select Worker model"></select>
    </div>
  </div>

  <div class="input-area">
    <textarea id="goal" placeholder="Describe the goal, e.g. 'Add a REST endpoint that lists all TODO items'" spellcheck="false"></textarea>
    <div class="button-row">
      <button class="primary" id="executeBtn" type="button">▶ Execute</button>
      <button class="secondary" id="stopBtn" type="button" disabled>■ Stop</button>
      <button class="secondary" id="resetBtn" type="button">↺ Reset</button>
    </div>
    <div class="hint">Worker indexes & drafts · Master plans & reviews · keys never leave your machine</div>
  </div>

  <div class="footer">MasterX · asymmetric Master-Worker orchestration</div>

  <script nonce="${nonce}">
    (function () {
      var vscode = acquireVsCodeApi();
      var busy = false;
      var stopRequested = false;

      var els = {
        masterModel: document.getElementById('masterModel'),
        workerModel: document.getElementById('workerModel'),
        goal: document.getElementById('goal'),
        executeBtn: document.getElementById('executeBtn'),
        stopBtn: document.getElementById('stopBtn'),
        resetBtn: document.getElementById('resetBtn'),
        tracker: document.getElementById('tracker'),
        stageEmpty: document.getElementById('stageEmpty'),
        console: document.getElementById('console'),
        logCount: document.getElementById('logCount')
      };

      var STAGE_TITLES = {
        indexing: 'Scout (worker)',
        planning: 'Plan (master)',
        executing: 'Execute (worker)',
        completed: 'Verify (master)'
      };
      var CUSTOM = '__custom__';
      var state = { masterModel: '', workerModel: '', models: [] };
      var logTotal = 0;

      function post(msg) {
        vscode.postMessage(msg);
      }

      function setBusy(value) {
        busy = value;
        els.executeBtn.disabled = value;
        els.stopBtn.disabled = !value;
        els.executeBtn.textContent = value ? '⏳ Running…' : '▶ Execute';
      }

      function dashRule() {
        var count = Math.max(24, Math.floor((els.console.clientWidth - 12) / 9));
        var rule = '';
        while (rule.length < count) { rule += '-'; }
        return rule;
      }

      function pushLine(cls, text) {
        var line = document.createElement('div');
        line.className = 'log-line ' + cls;
        line.textContent = text;
        els.console.appendChild(line);
        logTotal += 1;
        els.logCount.textContent = String(logTotal);
        els.console.scrollTop = els.console.scrollHeight;
        while (els.console.childElementCount > 800) {
          els.console.removeChild(els.console.firstChild);
        }
        return line;
      }

      function appendLog(message, level) {
        pushLine(level || 'info', message);
      }

      function appendUserEntry(text) {
        pushLine('user', text);
        pushLine('separator', dashRule());
      }

      function appendMasterReport(text) {
        var line = pushLine('master', '');
        var label = document.createElement('span');
        label.className = 'entry-label';
        label.textContent = 'Master: ';
        line.appendChild(label);
        line.appendChild(document.createTextNode(text));
      }

      function clearStages() {
        var rows = els.tracker.querySelectorAll('.stage-row');
        for (var i = 0; i < rows.length; i++) {
          els.tracker.removeChild(rows[i]);
        }
        els.stageEmpty.style.display = 'block';
      }

      function stageRow(stage) {
        var row = els.tracker.querySelector('.stage-row[data-stage="' + stage + '"]');
        if (row) { return row; }
        row = document.createElement('div');
        row.className = 'stage-row status-running';
        row.setAttribute('data-stage', stage);
        var head = document.createElement('div');
        head.className = 'stage-head';
        var dot = document.createElement('span');
        dot.className = 'dot';
        var title = document.createElement('span');
        title.className = 'stage-title';
        title.textContent = STAGE_TITLES[stage] || stage;
        var chevron = document.createElement('span');
        chevron.className = 'chevron';
        chevron.textContent = '▾';
        head.appendChild(dot);
        head.appendChild(title);
        head.appendChild(chevron);
        var detail = document.createElement('div');
        detail.className = 'stage-detail';
        row.appendChild(head);
        row.appendChild(detail);
        row.addEventListener('click', function () {
          row.classList.toggle('expanded');
        });
        els.tracker.appendChild(row);
        els.stageEmpty.style.display = 'none';
        return row;
      }

      function markRunningDone() {
        var running = els.tracker.querySelectorAll('.stage-row.status-running');
        for (var i = 0; i < running.length; i++) {
          running[i].classList.remove('status-running');
          running[i].classList.add('status-done');
        }
      }

      function setStage(stage, detail) {
        if (stage === 'error') {
          var stopped = stopRequested;
          var row = els.tracker.querySelector('.stage-row.status-running');
          if (row) {
            row.classList.remove('status-running');
            row.classList.add(stopped ? 'status-stopped' : 'status-failed');
            row.querySelector('.stage-detail').textContent = detail || '';
          }
          if (detail) {
            appendLog(stopped ? 'Stopped: ' + detail : 'FAILED: ' + detail, stopped ? 'warn' : 'error');
          }
          return;
        }
        var active = stageRow(stage);
        var running = els.tracker.querySelectorAll('.stage-row.status-running');
        for (var i = 0; i < running.length; i++) {
          if (running[i] !== active) {
            running[i].classList.remove('status-running');
            running[i].classList.add('status-done');
          }
        }
        active.classList.remove('status-done');
        active.classList.remove('status-failed');
        active.classList.add('status-running');
        active.querySelector('.stage-detail').textContent = detail || '';
        pushLine('stage-banner', STAGE_TITLES[stage] || stage);
      }

      function setDone() {
        markRunningDone();
      }

      function fillSelect(select, current) {
        select.innerHTML = '';
        var auto = document.createElement('option');
        auto.value = 'Auto';
        auto.textContent = 'Auto';
        select.appendChild(auto);
        if (!current) {
          var unset = document.createElement('option');
          unset.value = '';
          unset.textContent = '(unset)';
          select.appendChild(unset);
        }
        var inCatalog = false;
        for (var i = 0; i < state.models.length; i++) {
          if (state.models[i] === current) { inCatalog = true; }
          var opt = document.createElement('option');
          opt.value = state.models[i];
          opt.textContent = state.models[i];
          select.appendChild(opt);
        }
        if (current && current !== 'Auto' && !inCatalog) {
          var custom = document.createElement('option');
          custom.value = current;
          custom.textContent = current + ' (custom)';
          select.appendChild(custom);
        }
        var entry = document.createElement('option');
        entry.value = CUSTOM;
        entry.textContent = 'Enter a model id…';
        select.appendChild(entry);
        select.value = current;
      }

      function renderModels() {
        fillSelect(els.masterModel, state.masterModel);
        fillSelect(els.workerModel, state.workerModel);
      }

      function wireSelect(select, role) {
        select.addEventListener('change', function () {
          var value = select.value;
          if (value === CUSTOM) {
            select.value = role === 'master' ? state.masterModel : state.workerModel;
            post({ type: 'custom-model', role: role });
            return;
          }
          var current = role === 'master' ? state.masterModel : state.workerModel;
          if (value !== current) {
            post({ type: 'set-model', role: role, model: value });
          }
        });
      }
      wireSelect(els.masterModel, 'master');
      wireSelect(els.workerModel, 'worker');

      els.executeBtn.addEventListener('click', function () {
        if (busy) { return; }
        var goal = els.goal.value.trim();
        if (!goal) {
          appendLog('Enter a goal before executing.', 'warn');
          return;
        }
        post({ type: 'execute', goal: goal });
      });

      els.stopBtn.addEventListener('click', function () {
        if (!busy) { return; }
        stopRequested = true;
        els.stopBtn.disabled = true;
        var row = els.tracker.querySelector('.stage-row.status-running');
        if (row) {
          row.querySelector('.stage-detail').textContent = 'Stopping…';
        }
        post({ type: 'stop' });
      });

      els.resetBtn.addEventListener('click', function () {
        if (busy) {
          appendLog('Wait for the current run to finish before resetting.', 'warn');
          return;
        }
        post({ type: 'reset' });
      });

      els.goal.addEventListener('keydown', function (event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
          event.preventDefault();
          els.executeBtn.click();
        }
      });

      window.addEventListener('message', function (event) {
        var msg = event.data;
        if (!msg || !msg.type) { return; }

        switch (msg.type) {
          case 'init':
            state.masterModel = msg.masterModel || '';
            state.workerModel = msg.workerModel || '';
            renderModels();
            break;

          case 'models':
            state.models = msg.models || [];
            renderModels();
            break;

          case 'log':
            appendLog(msg.message, msg.level);
            break;

          case 'user-input':
            stopRequested = false;
            appendUserEntry(msg.text || '');
            clearStages();
            stageRow('indexing').querySelector('.stage-detail').textContent = 'Starting…';
            break;

          case 'stage':
            setStage(msg.stage, msg.detail);
            break;

          case 'summary':
            appendMasterReport(msg.text || '');
            setDone();
            break;

          case 'busy':
            setBusy(!!msg.value);
            break;

          case 'reset':
            clearStages();
            logTotal = 0;
            els.logCount.textContent = '0';
            els.console.innerHTML = '';
            stopRequested = false;
            break;

          case 'focus-input':
            els.goal.focus();
            break;

          case 'do-execute':
            els.executeBtn.click();
            break;
        }
      });

      post({ type: 'ready' });
    })();
  </script>
</body>
</html>`;
  }
}

/** CSP nonce for the inline script. */
function getNonce(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let text = '';
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
