export type Role = 'ADMIN' | 'PROJECT_MANAGER' | 'DEVELOPER';
export type ProjectRole = 'MANAGER' | 'MEMBER';
export type Tier = 'WORKER' | 'EXPERT';
export type BudgetState = 'OK' | 'WARNING' | 'EXCEEDED' | 'NONE';
export type Outcome = 'SUCCESS' | 'ERROR' | 'WORKER_ONLY';
export type StatusCategory = 'TODO' | 'IN_PROGRESS' | 'DONE';

export interface CurrentUser {
  id: number;
  email: string;
  displayName: string;
  role: Role;
  projects: { id: number; key: string; name: string; roleInProject: ProjectRole }[];
}

export interface Kpis {
  totalTokens: number;
  workerTokens: number;
  expertTokens: number;
  workerCost: number;
  expertCost: number;
  totalCost: number;
  baselineCost: number;
  savings: number;
  savingsPct: number;
  requests: number;
  activeDevelopers: number;
  storiesAssigned: number;
  storiesDone: number;
  costPerStory: number | null;
}
export interface KpiBlock {
  current: Kpis;
  previous: Kpis;
}

export interface DailyPoint {
  day: string;
  workerTokens: number;
  expertTokens: number;
  cost: number;
  baselineCost: number;
  savings: number;
  requests: number;
}
export interface ModelUsage {
  modelId: number;
  model: string;
  provider: string;
  tier: Tier;
  tokens: number;
  cost: number;
  requests: number;
}

export interface ModelRef {
  id: number;
  name: string;
  provider: string;
  tier: Tier;
}
export interface Routing {
  workerModel: ModelRef;
  expertModel: ModelRef;
  source: 'GLOBAL' | 'PROJECT' | 'USER';
  configVersion: number;
}

export interface ProjectSummary {
  id: number;
  key: string;
  name: string;
  developers: number;
  totalTokens: number;
  workerTokens: number;
  expertTokens: number;
  cost: number;
  savings: number;
  storiesAssigned: number;
  storiesDone: number;
  budgetUsd: number | null;
  budgetUsedPct: number | null;
}
export interface DeveloperRow {
  userId: number;
  displayName: string;
  email: string;
  workerTokens: number;
  expertTokens: number;
  cost: number;
  savings: number;
  requests: number;
  storiesAssigned: number;
  storiesDone: number;
  costPerStory: number | null;
  override: { workerModel: ModelRef; expertModel: ModelRef } | null;
  lastActive: string | null;
}
export interface UsageEventRow {
  eventId: string;
  timestamp: string;
  projectKey: string;
  workerModel: string;
  expertModel: string | null;
  workerTokens: number;
  expertTokens: number;
  latencyMs: number;
  cost: number;
  savings: number;
  jiraKey: string | null;
  outcome: Outcome;
}
export interface JiraIssueRow {
  key: string;
  summary: string;
  status: string;
  statusCategory: StatusCategory;
  assignee: string;
  updatedAt: string;
  resolvedAt: string | null;
  url: string | null;
}
export interface Page<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
}

export interface Overview {
  kpis: KpiBlock;
  daily: DailyPoint[];
  byModel: ModelUsage[];
  projects: ProjectSummary[];
  topDevelopers: DeveloperRow[];
}

export interface ProjectDetail {
  project: {
    id: number;
    key: string;
    name: string;
    jiraProjectKey: string | null;
    budgetUsd: number | null;
    alertPct: number;
    budgetUsedUsd: number;
    budgetUsedPct: number | null;
    budgetState: BudgetState;
    managers: { id: number; displayName: string }[];
  };
  routing: Routing;
  kpis: KpiBlock;
  daily: DailyPoint[];
  byModel: ModelUsage[];
  developers: DeveloperRow[];
}
export interface DeveloperDetail {
  user: { id: number; displayName: string; email: string; role: Role };
  project: { id: number; key: string; name: string } | null;
  routing: Routing;
  kpis: KpiBlock;
  daily: DailyPoint[];
  byModel: ModelUsage[];
  events: Page<UsageEventRow>;
  jiraIssues: JiraIssueRow[];
}

export interface Model extends ModelRef {
  enabled: boolean;
  inputPer1k: number;
  outputPer1k: number;
  priceSince: string;
}

export interface AdminUser {
  id: number;
  email: string;
  displayName: string;
  role: Role;
  status: 'ACTIVE' | 'DISABLED';
  jiraAccountId: string | null;
  lastSeen: string | null;
  projects: { projectId: number; key: string; name: string; roleInProject: ProjectRole }[];
  apiKeys: { id: number; label: string; prefix: string; createdAt: string; revokedAt: string | null; lastUsedAt: string | null }[];
}
export interface ProjectMemberRow {
  projectId: number;
  projectKey: string;
  projectName: string;
  userId: number;
  displayName: string;
  email: string;
  workerModel: ModelRef;
  expertModel: ModelRef;
  isOverride: boolean;
  cost: number;
  savings: number;
  requests: number;
  storiesAssigned: number;
  storiesDone: number;
  costPerStory: number | null;
  lastActive: string | null;
}

export interface AdminProject {
  id: number;
  key: string;
  name: string;
  jiraProjectKey: string | null;
  budgetUsd: number | null;
  alertPct: number;
  memberCount: number;
  managers: string[];
}
export interface AuditEntry {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  entityId: string | null;
  before: unknown;
  after: unknown;
}