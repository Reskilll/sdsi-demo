# MesterX Usage Dashboard — Product & Technical Plan

| Field | Value |
|---|---|
| Document status | Draft v1.0 |
| Date | 2026-10-28 |
| Owner | MesterX team |
| Audience | Engineering, Product, Project Managers |

---

## 1. Background

MesterX is an IDE plugin that routes every developer request through a **two-tier LLM pipeline**:

1. **Worker tier (free / open models)** — e.g. Qwen, Gemma. Reads and understands the codebase, builds context, and prepares a compact task description.
2. **Expert tier (paid models)** — e.g. Claude Opus 5.5. Receives only the distilled context and produces the final answer.

The goal of this design is to cut paid-model token spend. Today the plugin is built and in use, but **nobody can see how much it is used, by whom, on which project, or how much money it actually saves**. Routing changes (which model is used at each tier) are also not controllable centrally.

## 2. Problem Statement

> Project managers and admins have no visibility into per-developer and per-project LLM token consumption, cost, or savings, and no way to control model routing or correlate usage with delivered work (Jira stories).

## 3. Goals

| # | Goal | Success measure |
|---|---|---|
| G1 | Full visibility of token usage per developer, per project, per model, per tier | Every plugin request is recorded and visible within 1 minute |
| G2 | Show cost and **estimated savings** vs. a "paid-model-only" baseline | Savings figure shown on every page, methodology documented |
| G3 | Let managers change the worker / expert model per project (or per user) | Change takes effect in the plugin within one request cycle |
| G4 | Correlate usage with delivered work | Jira stories assigned / completed shown next to token cost per developer |
| G5 | Role-based access: Admin sees everything, PM sees own projects, Developer sees own usage | Enforced server-side, verified by tests |

### Non-goals (v1)

- Billing or invoicing integration with LLM vendors.
- Replacing the plugin's routing logic (the dashboard only *configures* it).
- Prompt / response content storage. We store **metadata only** (counts, model, timing), never code or prompt text.

## 4. Users & Roles

| Role | Who | Can see | Can do |
|---|---|---|---|
| **Admin** | Platform / engineering leadership | All projects, all users, global totals | Create projects, assign PMs, set global default models, manage model catalogue and pricing, manage users and API keys |
| **Project Manager** | Lead of one or more projects | Own project(s) only: per-developer usage, cost, savings, Jira stories | Change worker / expert model for their project, set per-user override, set monthly token budget & alerts, export CSV |
| **Developer** | Plugin end user | Own usage only | View personal usage, see which models are currently assigned to them |

## 5. Key Metrics & Definitions

| Metric | Definition |
|---|---|
| Worker tokens | Input + output tokens consumed by the free-tier model |
| Expert tokens | Input + output tokens consumed by the paid-tier model |
| Expert cost (USD) | Σ (tokens × price per 1K tokens for that model, split by input/output) |
| Worker cost (USD) | Usually $0 for self-hosted / free models; configurable in the model catalogue |
| **Baseline cost** | What the request *would* have cost if the expert model had processed the full raw context. Computed as `(worker input tokens + expert tokens) × expert price` |
| **Savings (USD)** | `Baseline cost − (Expert cost + Worker cost)` |
| Savings % | `Savings / Baseline cost` |
| Requests | Number of plugin invocations |
| Jira stories assigned / done | Count of issues assigned to the user in the selected period, and count moved to Done |
| Cost per story | `Total cost / stories done` (shown only when stories done > 0) |

The baseline formula is an **estimate** and must be labelled as such in the UI with a tooltip explaining the method.

### 5.1 Claude Enterprise Plan ($50 / dev / month) Governance

Organizations subscribing to Claude Enterprise / Team seats at **$50/seat/month** face severe quota burnout under raw direct Claude usage. MesterX provides governance and economic amplification for this tier:

1. **Context Distillation**: Ingests 85% of codebase tokens via open worker models ($0.00), passing only concise payloads to Claude.
2. **Predictable Spend**: Keeps average Claude consumption at **$12 to $22 per developer per month**, ensuring **0% budget overrun risk** and leaving a >50% safety buffer.
3. **5x Value Multiplier**: Yields 4x to 6x more completions and code intelligence value under the exact same $50 subscription.
4. **Automated Quota Alerts**:
   - `0% - 70%`: Normal dual-tier routing.
   - `70% - 85%`: Budget warning banner in IDE and dashboard.
   - `85%+`: Intelligent fallback circuit breaker preserving Claude quota for critical high-complexity tasks.

## 6. Pages & Layout

All pages share: top bar (logo, project switcher, date-range picker, user menu), left navigation, and a filter row (date range, project, model, user).

### 6.1 Admin — Global Overview (`/admin`)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ MesterX Admin        [ Project: All ▾ ]  [ Last 30 days ▾ ]      admin ▾   │
├──────────┬─────────────────────────────────────────────────────────────────┤
│ Overview │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ Projects │  │ Total    │ │ Expert   │ │ Est.     │ │ Active   │            │
│ Users    │  │ Tokens   │ │ Cost $   │ │ Savings $│ │ Devs     │            │
│ Models   │  │ 48.2M    │ │ 1,240    │ │ 3,870 ▲  │ │ 37       │            │
│ Settings │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│ Audit    │                                                                 │
│          │  Daily tokens — Worker vs Expert (stacked area)                 │
│          │  ┌───────────────────────────────────────────────────────────┐  │
│          │  │ ▓▓▓▓▓▓▓░░░░▓▓▓▓▓▓▓▓░░░░▓▓▓▓▓▓▓▓▓▓░░░░░▓▓▓▓▓▓▓▓▓░░░░░░       │  │
│          │  └───────────────────────────────────────────────────────────┘  │
│          │                                                                 │
│          │  Projects                                                       │
│          │  ┌────────────┬────────┬────────┬────────┬────────┬──────────┐  │
│          │  │ Project    │ Devs   │ Tokens │ Cost $ │ Save $ │ Stories  │  │
│          │  ├────────────┼────────┼────────┼────────┼────────┼──────────┤  │
│          │  │ Payments   │ 12     │ 18.1M  │  480   │ 1,520  │ 64 / 51  │  │
│          │  │ Mobile     │  9     │ 11.4M  │  310   │   940  │ 42 / 37  │  │
│          │  │ …          │        │        │        │        │          │  │
│          │  └────────────┴────────┴────────┴────────┴────────┴──────────┘  │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

Widgets:
- **KPI tiles**: total tokens, expert cost, estimated savings, active developers, requests. Each shows delta vs. previous period.
- **Daily tokens** stacked area chart: worker vs expert.
- **Cost by model** bar chart.
- **Projects table**: sortable, click row → Project page.
- **Top 10 developers by cost** table (cross-project).

### 6.2 Admin — Models & Pricing (`/admin/models`)

- Model catalogue: name, provider, tier (worker / expert), input price / 1K, output price / 1K, enabled flag.
- Global default worker model and expert model.
- Price history is versioned so historical cost is not recalculated when prices change.

### 6.3 Admin — Users (`/admin/users`)

- List of users with role, projects, Jira account link, plugin API key status (active / revoked), last seen.
- Invite user, assign role, assign to project, revoke key.

### 6.4 Admin — Audit Log (`/admin/audit`)

- Every configuration change: who, when, what changed (old → new). Required because model changes directly affect cost.

### 6.5 Project Manager — Project Page (`/projects/{id}`)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Payments            [ Last 30 days ▾ ]  [ Export CSV ]        pm.jane ▾    │
├────────────────────────────────────────────────────────────────────────────┤
│ Model routing                                                              │
│  Worker model : [ Qwen 2.5 Coder 32B ▾ ]   Expert model : [ Claude Opus 5.5 ▾ ]  [Save] │
│  Monthly budget: [ $600 ]   Alert at: [ 80 % ]        Used this month: 72 % ████████░░ │
├────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│ │ Tokens   │ │ Cost $   │ │ Savings $│ │ Requests │ │ Stories  │          │
│ │ 18.1M    │ │ 480      │ │ 1,520    │ │ 2,314    │ │ 64 / 51  │          │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                            │
│ Developers                                                                 │
│ ┌───────────┬──────────┬──────────┬────────┬────────┬───────────┬────────┐ │
│ │ Developer │ Worker   │ Expert   │ Cost $ │ Save $ │ Stories   │ Model  │ │
│ │           │ tokens   │ tokens   │        │        │ assigned/ │ override│ │
│ │           │ (Qwen)   │ (Claude) │        │        │ done      │        │ │
│ ├───────────┼──────────┼──────────┼────────┼────────┼───────────┼────────┤ │
│ │ a.kumar   │ 3.2M     │ 410K     │  96    │  310   │ 9 / 8     │  —  ✎  │ │
│ │ s.lee     │ 2.8M     │ 520K     │ 122    │  280   │ 7 / 5     │ Sonnet ✎│ │
│ │ …         │          │          │        │        │           │        │ │
│ └───────────┴──────────┴──────────┴────────┴────────┴───────────┴────────┘ │
│                                                                            │
│ Daily cost (line)                 │  Cost per story by developer (bar)     │
└────────────────────────────────────────────────────────────────────────────┘
```

Behaviour:
- **Model routing panel**: changing a model requires a confirmation dialog showing the price difference. Change is written to the audit log and pushed to the plugin on its next config poll.
- **Developers table**: one row per developer; columns for worker tokens, expert tokens, cost, savings, Jira stories (assigned / done), cost per story, and a per-user model override. Click a row → Developer detail.
- **Budget bar**: turns amber at alert threshold, red at 100 %. Optional hard stop (plugin falls back to worker-only) is a v2 item.

### 6.6 Developer Detail (`/projects/{id}/users/{userId}`)

- KPI tiles for the developer.
- Daily token chart (worker vs expert).
- Request log table: timestamp, worker model, expert model, worker tokens, expert tokens, latency, cost, linked Jira key (if the plugin was given one). **No prompt or code content.**
- Jira stories list for the period with status.

### 6.7 Developer — My Usage (`/me`)clau

Same as 6.6 but for the logged-in user only, read-only, plus a banner showing "Your current models: Qwen 2.5 Coder → Claude Opus 5.5".

## 7. Data Flow & Architecture

```
┌──────────────┐  POST /api/v1/events (batched)   ┌──────────────────────┐
│ MesterX      │ ───────────────────────────────▶ │ Dashboard Backend    │
│ IDE Plugin   │ ◀─────────────────────────────── │ (Java 21, Spring Boot)│
│              │  GET /api/v1/config (poll 60 s)  │                      │
└──────────────┘                                  │  ├─ Ingest service    │
                                                  │  ├─ Aggregation jobs  │
                                                  │  ├─ Config service    │
                                                  │  ├─ Jira sync job     │
                                                  │  └─ REST API for UI   │
┌──────────────┐                                  └──────────┬───────────┘
│ Jira Cloud   │ ◀── REST (issues assigned per user) ────────┤
└──────────────┘                                             │
                                                  ┌──────────▼───────────┐
┌──────────────┐  HTTPS / JSON                    │ PostgreSQL            │
│ Web UI (SPA) │ ◀──────────────────────────────▶ │ raw events + daily    │
│ React + TS   │                                  │ rollups + config      │
└──────────────┘                                  └──────────────────────┘
```

### 7.1 Technology choices

| Layer | Choice | Reason |
|---|---|---|
| Backend | Java 21, Spring Boot 3, Spring Security, Spring Data JPA, Flyway | Matches existing Java project; mature auth and scheduling |
| Database | PostgreSQL 16 | Strong aggregation, JSONB for event payloads, free |
| Frontend | React + TypeScript, Vite, a charting library (e.g. Recharts), a data-grid component | Fast dashboards, wide component ecosystem |
| Auth | OIDC / SSO (company IdP) for the web UI; per-user API keys for the plugin | Avoid custom passwords; keys can be revoked individually |
| Jobs | Spring `@Scheduled` (v1), move to a queue if volume demands | Simplicity first |
| Deployment | Docker Compose (dev), Kubernetes or a single VM (prod) | Standard |

### 7.2 Plugin → Dashboard contract

The plugin already exists, so this is the only change it needs: emit one event per request and poll config.

**Event** (`POST /api/v1/events`, header `X-Api-Key`):

```json
{
  "events": [
    {
      "eventId": "uuid",
      "timestamp": "2026-10-28T09:41:12Z",
      "projectKey": "PAYMENTS",
      "worker": { "model": "qwen2.5-coder-32b", "inputTokens": 14230, "outputTokens": 812, "latencyMs": 2100 },
      "expert": { "model": "claude-opus-5-5", "inputTokens": 1890, "outputTokens": 640, "latencyMs": 5400 },
      "jiraKey": "PAY-412",
      "outcome": "SUCCESS",
      "pluginVersion": "1.4.0"
    }
  ]
}
```

Events are idempotent on `eventId`; the plugin may batch and retry.

**Config** (`GET /api/v1/config`):

```json
{
  "workerModel": "qwen2.5-coder-32b",
  "expertModel": "claude-opus-5-5",
  "budgetState": "OK",
  "configVersion": 17
}
```

Resolution order: user override → project setting → global default.

### 7.3 Data model (core tables)

| Table | Key columns |
|---|---|
| `users` | id, email, display_name, role, jira_account_id, status |
| `projects` | id, key, name, jira_project_key, budget_usd, alert_pct |
| `project_members` | project_id, user_id, role_in_project |
| `models` | id, name, provider, tier, enabled |
| `model_prices` | model_id, input_per_1k, output_per_1k, valid_from, valid_to |
| `routing_config` | scope (GLOBAL / PROJECT / USER), scope_id, worker_model_id, expert_model_id, version, updated_by, updated_at |
| `api_keys` | id, user_id, key_hash, created_at, revoked_at |
| `usage_events` | event_id, ts, user_id, project_id, worker_model_id, expert_model_id, worker_in, worker_out, expert_in, expert_out, cost_usd, baseline_usd, jira_key, outcome |
| `usage_daily` | day, user_id, project_id, model_id, tier, tokens_in, tokens_out, cost_usd, baseline_usd, requests |
| `jira_issues` | key, project_id, assignee_user_id, status, created_at, resolved_at, synced_at |
| `audit_log` | id, ts, actor_id, action, entity, before_json, after_json |

Cost is computed **at ingest time** with the price valid at that timestamp and stored on the event, so later price changes never rewrite history.

### 7.4 Jira integration

- Jira Cloud REST API with a service account token.
- Sync every 15 minutes: for each project, fetch issues assigned to project members updated since last sync.
- Map Jira accounts to dashboard users by email; admins can fix mismatches manually.
- "Assigned" = issues with assignee = user and created or active within period. "Done" = status category `Done` with `resolved_at` within period.

## 8. Security & Privacy

- Store usage metadata only; **never** prompt text, code, or model output.
- API keys stored hashed; shown once at creation.
- All role checks enforced in the backend; the UI only hides what the API already forbids.
- Audit log is append-only.
- HTTPS everywhere; rate-limit the event endpoint per key.

## 9. Delivery Plan

| Phase | Scope | Duration (est.) | Exit criteria |
|---|---|---|---|
| **0 – Foundation** | Repo structure, Spring Boot skeleton, Postgres + Flyway, CI, auth with roles, Docker Compose | 1–2 weeks | Login works with 3 roles; empty pages render |
| **1 – Ingest & Admin overview** | Event endpoint, API keys, cost calculation, daily rollups, model catalogue + pricing, Admin overview page | 2–3 weeks | Plugin sends real events; admin sees tokens, cost, savings |
| **2 – Project & Developer pages** | Project page with developer table, developer detail, My Usage page, CSV export | 2 weeks | PM sees their project only; developer sees self only |
| **3 – Model routing control** | Config endpoint, routing panel, per-user override, audit log, plugin polling change | 1–2 weeks | PM changes model; plugin uses it on next request; audit entry created |
| **4 – Jira integration** | Jira sync job, account mapping, stories columns, cost-per-story chart | 1–2 weeks | Stories assigned / done appear per developer |
| **5 – Budgets & polish** | Monthly budget, alerts (email / Slack), dark mode, performance tuning, docs | 1–2 weeks | Alert fires at threshold; p95 page load < 2 s on 90-day range |

Total: roughly **9–13 weeks** for one full-stack engineer plus part-time plugin engineer. Phases 1 and 2 deliver the core value and can ship first.

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Savings estimate is challenged as inaccurate | Loss of trust in the headline number | Document formula in UI tooltip; allow admin to tune baseline assumptions; show tokens alongside dollars |
| Plugin telemetry changes slip | Dashboard has no data | Define the event contract (7.2) first and ship a plugin update in Phase 1 |
| Jira account mapping mismatches | Wrong stories per developer | Email-based auto-match plus manual admin override |
| Model price changes break historical cost | Misleading trends | Versioned `model_prices`; cost frozen at ingest |
| Developers feel surveilled | Adoption resistance | Metadata only, transparent "My Usage" page, no content stored, communicate purpose (cost, not performance review) |
| High event volume | Slow queries | Daily rollup table; UI reads rollups, raw events only in detail view |

## 11. Open Questions

1. Which identity provider (Google Workspace, Azure AD, Okta) should the web UI use for SSO?
2. Is Jira Cloud or Jira Data Center in use? Authentication differs.
3. Should a "hard stop" at 100 % budget force the plugin to worker-only mode, or only alert?
4. Does the plugin already know the Jira key for a task (e.g. from branch name), or must the developer enter it?
5. Are worker models self-hosted (cost $0) or via a paid API (e.g. Together, Groq)? This affects the worker cost column.
6. Should managers be able to see request-level logs for developers, or only aggregates?

## 12. Next Steps

1. Review this plan and answer the open questions in section 11.
2. Agree the event contract in section 7.2 with the plugin team.
3. Start Phase 0: convert this module to a Spring Boot + Maven/Gradle project and set up Postgres via Docker Compose.

---

## Appendix A — Original brief (verbatim)

> I want to creat a dashboard where we can see the data regarding users/developer who are using our new plangin that is MesterX which use 2 model one as worker which will be free llm models like qwen. gama, etc which will work first to understant the code and thenn it will transfer to paid llm like claude opus 5.5 etc this it is the logic of our plugin to save cost of paid llm and save token ok which we have build already now
> issue is where we will trace this data so what we came with idea that there should be a dahborad where project manager can see the user/developer wise the token uses by qwen or claude model and manager can change the llm and respective uses can see and also one more coloum which should add no of task or jira story assigned to that users so to monitor the token cost dollor save and jira story
>
> so i want that there should be a admin page also and then project wise page where project manager can see and admin can see whole thing so let s make plan first with how it should look like.
> so create plan here.
