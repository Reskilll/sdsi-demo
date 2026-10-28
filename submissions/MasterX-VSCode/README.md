# MasterX

**Asymmetric Master-Worker orchestration for VS Code.** Two separate `claude` CLI instances with **different models**: a cheap Worker indexes and drafts, a deep-thinking Master plans and reviews. You spend high-tier tokens only on reasoning — never on raw source dumps.

## How it works

| Stage | Who | Model | What |
|-------|-----|-------|------|
| 1 · Indexing | **Worker** | lighter (e.g. `deepseek/deepseek-v4-flash`) | Scans the workspace, samples file contents, emits a dense architectural summary |
| 2 · Planning | **Master** | deep (e.g. `xiaomi/mimo-v2.6-pro`) | Reads **only the summary**, reasons deeply, emits a strict JSON plan of `create_file` / `edit_file` / `run_command` tasks |
| 3 · Execution | **Worker** | lighter | Drafts complete file contents and command lines to the Master's spec |
| 4 · Synthesis | **Master** | deep | Reviews execution logs and writes the final report |

Each step is its own `claude --print` invocation bound to its own `--model`. Every step streams to the sidebar console as it happens.

## Install

```bash
npm install
npm run compile
```

Then press **F5** (Run Extension) in VS Code.

**Requirement:** the Claude CLI must be installed and on `PATH` —
`npm install -g @anthropic-ai/claude-code`, or set `masterx.claudeCliPath`.

## Where to configure the models

Models are chosen from a **dropdown**, not typed into settings. The dropdown is
populated from an OpenAI-compatible `GET /v1/models` endpoint.

### 1. Pick the models (the normal path)

| Do this | Or this |
|---------|---------|
| Click the **Master** / **Worker** row in the sidebar panel | `Ctrl+Shift+P` → **MasterX: Select Master Model** / **Select Worker Model** |

Either way you get a searchable dropdown of every model the endpoint reports.
The choice is saved to `masterx.masterModel` / `masterx.workerModel`, and the
status bar updates immediately. If the catalog can't be reached, the picker
falls back to typing a model id by hand — you are never blocked.

### 2. The OpenAI API key

`Ctrl+,` → search **`@ext:masterx openAiApiKey`**, or set `OPENAI_API_KEY` in
the environment. It is used twice:

1. to fetch the model list for the dropdowns (`Authorization: Bearer …`), and
2. as the bearer token in the **run-scoped `settings.json`** each task run
   writes and hands to the `claude` CLI.

### 3. Where the key and models go at run time

Every task run writes a **run-scoped `settings.json`** in the temp directory and
passes it to each `claude` instance as `--settings <path>`:

```json
{
  "model": "xiaomi/mimo-v2.6-pro",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek/deepseek-v4-flash",
    "ANTHROPIC_AUTH_TOKEN": "<the OpenAI API key>",
    "ANTHROPIC_API_KEY": ""
  }
}
```

| Key in the run file | Comes from |
|---|---|
| `model` | **Master** dropdown |
| `env.CLAUDE_CODE_SUBAGENT_MODEL` | **Worker** dropdown |
| `env.ANTHROPIC_AUTH_TOKEN` | `masterx.openAiApiKey` |
| `env.ANTHROPIC_API_KEY` | explicitly blanked, so it can't shadow the token |
| everything else (base URL, …) | inherited from `~/.claude/settings.json` |

The CLI merges that file **key-wise** over `~/.claude/settings.json` (verified),
so only the overrides are written. **Your global `~/.claude/settings.json` is
never modified**, and the run file is deleted when the run finishes.

No OpenAI key set? Then no token is written at all and the CLI inherits whatever
`~/.claude/settings.json` already provides.

### 4. `~/.claude/settings.json` (still the fallback)

When the dropdowns have not been used yet, MasterX falls back to the same file
the Claude CLI reads:

```json
{
  "model": "opus",                                         // → Master
  "env": {
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "xiaomi/mimo-v2.6-pro",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek/deepseek-v4-flash"   // → Worker
  }
}
```

The sidebar and **Show Resolved Configuration** display the model *and* the
exact source it was read from, e.g.
`C:\Users\you\.claude\settings.json → env.CLAUDE_CODE_SUBAGENT_MODEL`, plus a
preview of what the next run's `settings.json` will contain.

### Resolution order

```
masterx.masterModel  →  ~/.claude/settings.json `model`  →  ANTHROPIC_MODEL  →  claude-opus-5-5
masterx.workerModel  →  CLAUDE_CODE_SUBAGENT_MODEL  →  ANTHROPIC_DEFAULT_HAIKU_MODEL  →  claude-haiku-5-5
```

### Settings reference

| Setting | Controls | Default |
|---------|----------|---------|
| `masterx.openAiApiKey` | Model-list key + run bearer token | `OPENAI_API_KEY` env |
| `masterx.modelListUrl` | Catalog endpoint | `https://creditclaim.reskilll.com/llm/v1/models` |
| `masterx.masterModel` | Master model (set by the dropdown) | from `~/.claude/settings.json` |
| `masterx.workerModel` | Worker model (set by the dropdown) | from `~/.claude/settings.json` |
| `masterx.claudeCliPath` | Absolute path to `claude` | `claude` on `PATH` |
| `masterx.useClaudeCliConfig` | Read defaults from `~/.claude/settings.json` | `true` |

Using a gateway instead of OpenAI? Point `masterx.modelListUrl` at that
gateway's `/v1/models` and the dropdown will list its models.

### 3. Environment variables (lowest precedence)

`ANTHROPIC_MODEL` (Master), `ANTHROPIC_DEFAULT_HAIKU_MODEL` (Worker fallback),
`CLAUDE_CODE_SUBAGENT_MODEL` (Worker), `CLAUDE_CLI_PATH` (binary).

### Resolution order

```
masterx.masterModel  →  ~/.claude/settings.json `model`  →  ANTHROPIC_MODEL  →  claude-opus-5-5
masterx.workerModel  →  CLAUDE_CODE_SUBAGENT_MODEL  →  ANTHROPIC_DEFAULT_HAIKU_MODEL  →  claude-haiku-5-5
```

Aliases (`opus`, `sonnet`, `haiku`, `fable`) expand exactly the way the Claude
CLI does, via `ANTHROPIC_DEFAULT_<ALIAS>_MODEL`, so the sidebar shows a real
model id.

**Verify what got picked up:** `Ctrl+Shift+P` → **`MasterX: Show Resolved
Configuration`**.

## Use

1. Open a workspace folder.
2. Click the **MasterX** icon in the Activity Bar.
3. Type a goal (e.g. *“Add a REST endpoint that lists all TODO items”*).
4. Press **Execute** (or `Ctrl+Enter`).

Watch the 4-stage tracker and console. The sidebar shows which model each side is running.

### Commands

| Command | What it does |
|---------|--------------|
| `MasterX: Select Master Model` | Dropdown of catalog models → Master |
| `MasterX: Select Worker Model` | Dropdown of catalog models → Worker |
| `MasterX: Execute Goal` | Focus the panel and start a run |
| `MasterX: Focus Panel` | Reveal the sidebar |
| `MasterX: Reset Panel` | Clear the tracker and console |
| `MasterX: Show Resolved Configuration` | Inspect the CLI, models, and the next run's `settings.json` |

## Design notes

- **Models come from a dropdown.** The catalog is fetched from an
  OpenAI-compatible `GET /v1/models`; if it can't be reached the picker falls
  back to typing an id by hand, so a network problem never blocks you.
- **Each run gets its own `settings.json`.** The model ids and the OpenAI API
  key are written to a temp file and passed to `claude` as `--settings`, which
  merges it key-wise over `~/.claude/settings.json`. The global file is never
  touched, and the run file is deleted afterwards.
- **The Worker is tool-light.** Indexing gets `Read`/`Glob`/`Grep` only; drafting
  gets **no tools** — it returns text that the extension writes itself. The
  Master gets no tools at all; it only reasons. This keeps both cheap and keeps
  the worker from driving your shell.
- **The Master's plan is structurally validated.** It is sent with
  `--json-schema`, and the extension re-checks every task
  (`action` / `targetPath` / `instructions`) before executing.
- **Commands run in `cmd.exe`** (on Windows), in a visible VS Code terminal, with
  output streamed live into the MasterX console and the real exit code captured.
- **File writes stay inside the workspace.** Any task path that resolves outside
  the root is refused.
- **No hardcoded credentials.** The OpenAI key comes from settings/environment
  and is only written into the per-run settings file, which is removed after.

## Architecture

```
src/
  types.ts           Shared contracts (SubTask, MasterPlan, TaskResult, messages)
  configLoader.ts    Resolves the two model ids, the key, and the claude CLI path
  modelCatalog.ts    GET /v1/models → dropdown entries
  runSettings.ts     Writes the run-scoped settings.json passed to `claude --settings`
  claudeCli.ts       Spawns `claude -p`, parses the result envelope
  master.ts          Master role: plan (JSON schema) + synthesize
  worker.ts          Worker role: index + draft files/commands
  orchestrator.ts    4-stage lifecycle with streaming hooks
  chatViewProvider.ts  Vanilla HTML/CSS/JS webview (no bundler, no framework)
  extension.ts       Activation + command registration
```

## Requirements

- VS Code `^1.85.0`
- Node `>= 18`
- Claude CLI 2.x installed and on `PATH`
- An OpenAI API key (`masterx.openAiApiKey` or `OPENAI_API_KEY`) — fetches the
  model dropdown and authenticates the run
- Two different model ids — that asymmetry is the whole point
