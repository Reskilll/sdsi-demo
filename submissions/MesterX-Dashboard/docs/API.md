# MesterX Dashboard — REST API Contract (v1)

All UI endpoints live under `/api/**`, are JSON, and use a **session cookie** (set by `/api/auth/login`).
Plugin endpoints live under `/api/v1/**` and use the `X-Api-Key` header.

Dates: query params `from` and `to` are ISO dates (`2026-10-01`), inclusive, UTC. Default = last 30 days.
Money: USD as decimal numbers (e.g. `12.3456`). Tokens: integers.

Errors: `{ "status": 403, "error": "Forbidden", "message": "..." }`.

---

## Auth

| Method | Path | Body / Params | Response |
|---|---|---|---|
| POST | `/api/auth/login` | `{ "email", "password" }` | `CurrentUser` (200) or 401 |
| POST | `/api/auth/logout` | – | 204 |
| GET | `/api/auth/me` | – | `CurrentUser` or 401 |

```ts
type Role = 'ADMIN' | 'PROJECT_MANAGER' | 'DEVELOPER';

interface CurrentUser {
  id: number; email: string; displayName: string; role: Role;
  projects: { id: number; key: string; name: string; roleInProject: 'MANAGER' | 'MEMBER' }[];
}
```

Dev seed accounts (profile `dev`):

| Email | Password | Role |
|---|---|---|
| admin@mesterx.io | admin123 | ADMIN |
| pm.jane@mesterx.io | pm123 | PROJECT_MANAGER (Payments, Mobile) |
| pm.raj@mesterx.io | pm123 | PROJECT_MANAGER (Data Platform) |
| a.kumar@mesterx.io | dev123 | DEVELOPER (Payments) |

---

## Shared shapes

```ts
interface Kpis {
  totalTokens: number; workerTokens: number; expertTokens: number;
  workerCost: number; expertCost: number; totalCost: number;
  baselineCost: number; savings: number; savingsPct: number;   // savingsPct 0..100
  requests: number; activeDevelopers: number;
  storiesAssigned: number; storiesDone: number; costPerStory: number | null;
}
interface KpiBlock { current: Kpis; previous: Kpis; }          // previous = same-length period before `from`

interface DailyPoint { day: string; workerTokens: number; expertTokens: number; cost: number; baselineCost: number; savings: number; requests: number; }
interface ModelUsage { modelId: number; model: string; provider: string; tier: 'WORKER' | 'EXPERT'; tokens: number; cost: number; requests: number; }

interface ModelRef { id: number; name: string; provider: string; tier: 'WORKER' | 'EXPERT'; }
interface Routing { workerModel: ModelRef; expertModel: ModelRef; source: 'GLOBAL' | 'PROJECT' | 'USER'; configVersion: number; }

interface ProjectSummary {
  id: number; key: string; name: string; developers: number;
  totalTokens: number; workerTokens: number; expertTokens: number;
  cost: number; savings: number; storiesAssigned: number; storiesDone: number;
  budgetUsd: number | null; budgetUsedPct: number | null;   // month-to-date
}
interface DeveloperRow {
  userId: number; displayName: string; email: string;
  workerTokens: number; expertTokens: number; cost: number; savings: number; requests: number;
  storiesAssigned: number; storiesDone: number; costPerStory: number | null;
  override: { workerModel: ModelRef; expertModel: ModelRef } | null;
  lastActive: string | null;   // ISO timestamp
}
interface UsageEventRow {
  eventId: string; timestamp: string; projectKey: string;
  workerModel: string; expertModel: string | null;
  workerTokens: number; expertTokens: number; latencyMs: number;
  cost: number; savings: number; jiraKey: string | null; outcome: 'SUCCESS' | 'ERROR' | 'WORKER_ONLY';
}
interface JiraIssueRow { key: string; summary: string; status: string; statusCategory: 'TODO' | 'IN_PROGRESS' | 'DONE'; assignee: string; updatedAt: string; resolvedAt: string | null; url: string | null; }
interface Page<T> { content: T[]; page: number; size: number; totalElements: number; totalPages: number; }
```

---

## Dashboard (Admin sees all projects; PM sees only their projects)

| Method | Path | Params | Response |
|---|---|---|---|
| GET | `/api/dashboard/overview` | `from`, `to`, optional `projectId` | `Overview` |

```ts
interface Overview {
  kpis: KpiBlock; daily: DailyPoint[]; byModel: ModelUsage[];
  projects: ProjectSummary[]; topDevelopers: DeveloperRow[];   // top 10 by cost
}
```

## Projects

| Method | Path | Body / Params | Response |
|---|---|---|---|
| GET | `/api/projects` | – | `ProjectSummary[]` (accessible projects, last 30 days) |
| GET | `/api/projects/{id}` | `from`, `to` | `ProjectDetail` |
| PUT | `/api/projects/{id}/routing` | `{ workerModelId, expertModelId }` | `Routing` |
| PUT | `/api/projects/{id}/budget` | `{ budgetUsd, alertPct }` | `ProjectDetail.project` |
| PUT | `/api/projects/{id}/members/{userId}/routing` | `{ workerModelId, expertModelId }` | `Routing` |
| DELETE | `/api/projects/{id}/members/{userId}/routing` | – | 204 (removes override) |
| GET | `/api/projects/{id}/members/{userId}` | `from`, `to`, `page`, `size` | `DeveloperDetail` |
| GET | `/api/projects/{id}/export.csv` | `from`, `to` | CSV file (developers table) |

```ts
interface ProjectDetail {
  project: { id: number; key: string; name: string; jiraProjectKey: string | null;
             budgetUsd: number | null; alertPct: number; budgetUsedUsd: number; budgetUsedPct: number | null;
             budgetState: 'OK' | 'WARNING' | 'EXCEEDED' | 'NONE'; managers: { id: number; displayName: string }[] };
  routing: Routing;
  kpis: KpiBlock; daily: DailyPoint[]; byModel: ModelUsage[];
  developers: DeveloperRow[];
}
interface DeveloperDetail {
  user: { id: number; displayName: string; email: string; role: Role };
  project: { id: number; key: string; name: string } | null;
  routing: Routing; kpis: KpiBlock; daily: DailyPoint[]; byModel: ModelUsage[];
  events: Page<UsageEventRow>; jiraIssues: JiraIssueRow[];
}
```

## Me (developer self-service)

| Method | Path | Params | Response |
|---|---|---|---|
| GET | `/api/me/usage` | `from`, `to`, `page`, `size` | `DeveloperDetail` (project = null, all projects of the user) |

## Models (read: any user; write: ADMIN)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/models` | – | `Model[]` |
| POST | `/api/admin/models` | `{ name, provider, tier, inputPer1k, outputPer1k, enabled }` | `Model` |
| PUT | `/api/admin/models/{id}` | `{ name, provider, tier, enabled }` | `Model` |
| PUT | `/api/admin/models/{id}/price` | `{ inputPer1k, outputPer1k }` (new version from now) | `Model` |

```ts
interface Model extends ModelRef { enabled: boolean; inputPer1k: number; outputPer1k: number; priceSince: string; }
```

## Admin

| Method | Path | Body / Params | Response |
|---|---|---|---|
| GET | `/api/admin/routing` | – | `Routing` (global default) |
| PUT | `/api/admin/routing` | `{ workerModelId, expertModelId }` | `Routing` |
| GET | `/api/admin/users` | – | `AdminUser[]` |
| POST | `/api/admin/users` | `{ email, displayName, role, password? }` | `AdminUser` |
| PUT | `/api/admin/users/{id}` | `{ displayName, role, status, jiraAccountId? }` | `AdminUser` |
| PUT | `/api/admin/users/{id}/projects` | `{ projects: { projectId, roleInProject }[] }` | `AdminUser` |
| POST | `/api/admin/users/{id}/api-keys` | `{ label }` | `{ id, label, plaintextKey, createdAt }` (key shown once) |
| DELETE | `/api/admin/api-keys/{keyId}` | – | 204 |
| GET | `/api/admin/projects` | – | `AdminProject[]` |
| POST | `/api/admin/projects` | `{ key, name, jiraProjectKey?, budgetUsd?, alertPct? }` | `AdminProject` |
| PUT | `/api/admin/projects/{id}` | same | `AdminProject` |
| GET | `/api/admin/audit` | `page`, `size` | `Page<AuditEntry>` |
| POST | `/api/admin/jira/sync` | – | `{ synced: number, lastSyncAt }` |

```ts
interface AdminUser { id: number; email: string; displayName: string; role: Role; status: 'ACTIVE' | 'DISABLED';
  jiraAccountId: string | null; lastSeen: string | null;
  projects: { projectId: number; key: string; name: string; roleInProject: 'MANAGER' | 'MEMBER' }[];
  apiKeys: { id: number; label: string; prefix: string; createdAt: string; revokedAt: string | null; lastUsedAt: string | null }[]; }
interface AdminProject { id: number; key: string; name: string; jiraProjectKey: string | null; budgetUsd: number | null; alertPct: number; memberCount: number; managers: string[]; }
interface AuditEntry { id: number; timestamp: string; actor: string; action: string; entity: string; entityId: string | null; before: unknown; after: unknown; }
```

---

## Plugin API (header `X-Api-Key: <key>`)

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/v1/events` | `{ events: PluginEvent[] }` | `{ accepted: number, duplicates: number }` |
| GET | `/api/v1/config` | optional `projectKey` | `{ workerModel, expertModel, budgetState, configVersion }` |

```ts
interface PluginEvent {
  eventId: string; timestamp: string; projectKey: string;
  worker: { model: string; inputTokens: number; outputTokens: number; latencyMs: number };
  expert?: { model: string; inputTokens: number; outputTokens: number; latencyMs: number };
  jiraKey?: string; outcome: 'SUCCESS' | 'ERROR' | 'WORKER_ONLY'; pluginVersion?: string;
}
```

Cost is computed at ingest with the price valid at `timestamp`:

```
workerCost   = worker.in/1000 * price.in + worker.out/1000 * price.out        (worker model price)
expertCost   = expert.in/1000 * price.in + expert.out/1000 * price.out        (expert model price)
baselineCost = (worker.in + expert.in)/1000 * expertPrice.in + (worker.out + expert.out)/1000 * expertPrice.out
savings      = baselineCost - (workerCost + expertCost)
```
