import type {
  AdminProject,
  AdminUser,
  AuditEntry,
  CurrentUser,
  DailyPoint,
  DeveloperDetail,
  DeveloperRow,
  JiraIssueRow,
  Kpis,
  Model,
  ModelRef,
  ModelUsage,
  Overview,
  ProjectDetail,
  ProjectMemberRow,
  ProjectSummary,
  UsageEventRow,
} from './types';

// ---------------------------------------------------------------------------
// Model Catalog
// ---------------------------------------------------------------------------

const WORKER_MODELS: ModelRef[] = [
  { id: 1, name: 'Qwen 2.5 Coder 32B', provider: 'Alibaba (Self-hosted)', tier: 'WORKER' },
  { id: 2, name: 'DeepSeek Coder V2', provider: 'DeepSeek (vLLM)', tier: 'WORKER' },
  { id: 3, name: 'Gemma 2 27B', provider: 'Google (Local)', tier: 'WORKER' },
  { id: 4, name: 'Llama 3.3 70B', provider: 'Meta (vLLM)', tier: 'WORKER' },
];

const EXPERT_MODELS: ModelRef[] = [
  { id: 10, name: 'Claude Sonnet 5.5', provider: 'Anthropic', tier: 'EXPERT' },
  { id: 11, name: 'Claude Opus 5.5', provider: 'Anthropic', tier: 'EXPERT' },
  { id: 12, name: 'GPT-5', provider: 'OpenAI', tier: 'EXPERT' },
  { id: 13, name: 'Gemini 2.5 Pro', provider: 'Google', tier: 'EXPERT' },
];

const ALL_MODELS: Model[] = [
  ...WORKER_MODELS.map((m) => ({
    ...m,
    enabled: true,
    inputPer1k: 0,
    outputPer1k: 0,
    priceSince: '2026-06-01T00:00:00Z',
  })),
  { id: 10, name: 'Claude Sonnet 5.5', provider: 'Anthropic', tier: 'EXPERT', enabled: true, inputPer1k: 0.003, outputPer1k: 0.015, priceSince: '2026-06-01T00:00:00Z' },
  { id: 11, name: 'Claude Opus 5.5', provider: 'Anthropic', tier: 'EXPERT', enabled: true, inputPer1k: 0.015, outputPer1k: 0.075, priceSince: '2026-06-01T00:00:00Z' },
  { id: 12, name: 'GPT-5', provider: 'OpenAI', tier: 'EXPERT', enabled: true, inputPer1k: 0.0025, outputPer1k: 0.01, priceSince: '2026-06-01T00:00:00Z' },
  { id: 13, name: 'Gemini 2.5 Pro', provider: 'Google', tier: 'EXPERT', enabled: true, inputPer1k: 0.00125, outputPer1k: 0.005, priceSince: '2026-06-01T00:00:00Z' },
];

// Blended cost per 1k tokens for quick calculation
const EXPERT_BLENDED_RATES: Record<number, number> = {
  10: 0.0055, // Claude Sonnet 5.5: ~$5.50 / 1M tokens blended
  11: 0.0280, // Claude Opus 5.5: ~$28.00 / 1M tokens blended
  12: 0.0045, // GPT-5: ~$4.50 / 1M tokens blended
  13: 0.0022, // Gemini 2.5 Pro: ~$2.20 / 1M tokens blended
};

// ---------------------------------------------------------------------------
// Developer Team Profiles
// ---------------------------------------------------------------------------

interface DevProfile {
  id: number;
  displayName: string;
  email: string;
  title: string;
  baseActivity: number; // multiplier
}

const DEVELOPERS: DevProfile[] = [
  { id: 101, displayName: 'Govind Chaubey', email: 'govind.chaubey@mesterx.io', title: 'Senior Backend Engineer', baseActivity: 1.25 },
  { id: 102, displayName: 'Abhishek Alwani', email: 'abhishek.alwani@mesterx.io', title: 'Fullstack & Rules Engineer', baseActivity: 1.10 },
  { id: 103, displayName: 'Yashwant', email: 'yashwant@mesterx.io', title: 'ML & Infrastructure Engineer', baseActivity: 0.95 },
  { id: 104, displayName: 'Dhiraj', email: 'dhiraj@mesterx.io', title: 'DevOps & Reliability Lead', baseActivity: 0.85 },
  { id: 105, displayName: 'Akhilesh', email: 'akhilesh@mesterx.io', title: 'Cloud & QA Systems Architect', baseActivity: 0.80 },
];

interface ProjectMemberAllocation {
  devId: number;
  workerModel?: ModelRef;
  expertModel?: ModelRef;
  storiesAssigned: number;
  storiesDone: number;
  weight: number; // share of project activity
}

interface ProjectSpec {
  id: number;
  key: string;
  name: string;
  jiraProjectKey: string;
  budgetUsd: number;
  managers: { id: number; displayName: string }[];
  defaultWorker: ModelRef;
  defaultExpert: ModelRef;
  allocations: ProjectMemberAllocation[];
}

const PROJECTS_CONFIG: ProjectSpec[] = [
  {
    id: 1,
    key: 'ANLYZR',
    name: 'Analyser',
    jiraProjectKey: 'ANLYZR',
    budgetUsd: 1200,
    managers: [{ id: 901, displayName: 'Priya Mehta' }],
    defaultWorker: WORKER_MODELS[0], // Qwen 2.5 Coder 32B
    defaultExpert: EXPERT_MODELS[0], // Claude Sonnet 5.5
    allocations: [
      { devId: 101, storiesAssigned: 14, storiesDone: 12, weight: 0.44 },
      { devId: 102, storiesAssigned: 11, storiesDone: 10, weight: 0.36 },
      { devId: 103, expertModel: EXPERT_MODELS[1], storiesAssigned: 7, storiesDone: 6, weight: 0.20 }, // Yashwant uses Claude Opus override
    ],
  },
  {
    id: 2,
    key: 'ARCHDEP',
    name: 'Architecture Deployment',
    jiraProjectKey: 'ARCHDEP',
    budgetUsd: 900,
    managers: [{ id: 902, displayName: 'Rajesh Iyer' }],
    defaultWorker: WORKER_MODELS[1], // DeepSeek Coder V2
    defaultExpert: EXPERT_MODELS[1], // Claude Opus 5.5
    allocations: [
      { devId: 103, storiesAssigned: 8, storiesDone: 7, weight: 0.38 },
      { devId: 104, storiesAssigned: 8, storiesDone: 6, weight: 0.34 },
      { devId: 105, storiesAssigned: 7, storiesDone: 6, weight: 0.28 },
    ],
  },
  {
    id: 3,
    key: 'JSM',
    name: 'JSM',
    jiraProjectKey: 'JSM',
    budgetUsd: 1500,
    managers: [{ id: 901, displayName: 'Priya Mehta' }],
    defaultWorker: WORKER_MODELS[0], // Qwen 2.5 Coder 32B
    defaultExpert: EXPERT_MODELS[2], // GPT-5
    allocations: [
      { devId: 101, storiesAssigned: 9, storiesDone: 8, weight: 0.58 },
      { devId: 104, storiesAssigned: 7, storiesDone: 6, weight: 0.42 },
    ],
  },
  {
    id: 4,
    key: 'CQE',
    name: 'CQE',
    jiraProjectKey: 'CQE',
    budgetUsd: 700,
    managers: [{ id: 902, displayName: 'Rajesh Iyer' }],
    defaultWorker: WORKER_MODELS[2], // Gemma 2 27B
    defaultExpert: EXPERT_MODELS[3], // Gemini 2.5 Pro
    allocations: [
      { devId: 102, storiesAssigned: 7, storiesDone: 6, weight: 0.55 },
      { devId: 105, storiesAssigned: 6, storiesDone: 5, weight: 0.45 },
    ],
  },
  {
    id: 5,
    key: 'PLATFORM',
    name: 'Platform Core',
    jiraProjectKey: 'PLATFORM',
    budgetUsd: 2000,
    managers: [{ id: 901, displayName: 'Priya Mehta' }, { id: 902, displayName: 'Rajesh Iyer' }],
    defaultWorker: WORKER_MODELS[0], // Qwen 2.5 Coder 32B
    defaultExpert: EXPERT_MODELS[0], // Claude Sonnet 5.5
    allocations: [
      { devId: 101, storiesAssigned: 7, storiesDone: 6, weight: 0.28 },
      { devId: 102, storiesAssigned: 6, storiesDone: 5, weight: 0.24 },
      { devId: 103, storiesAssigned: 5, storiesDone: 4, weight: 0.18 },
      { devId: 104, storiesAssigned: 5, storiesDone: 4, weight: 0.16 },
      { devId: 105, storiesAssigned: 5, storiesDone: 4, weight: 0.14 },
    ],
  },
];

// ---------------------------------------------------------------------------
// Time & Seed Setup
// ---------------------------------------------------------------------------

const DAYS = 30;
const END = new Date('2026-10-28T12:00:00Z');
const START = new Date(END.getTime() - (DAYS - 1) * 86400000);

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// Deterministic Pseudo-random
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------------------
// Realistic Data Engine
// ---------------------------------------------------------------------------

// Precomputed daily series per allocation
interface MemberDailyStats {
  projectId: number;
  devId: number;
  workerModel: ModelRef;
  expertModel: ModelRef;
  isOverride: boolean;
  storiesAssigned: number;
  storiesDone: number;
  daily: DailyPoint[];
}

const ALL_MEMBER_STATS: MemberDailyStats[] = [];

// Initialize realistic daily stats for each project member
for (const p of PROJECTS_CONFIG) {
  for (const alloc of p.allocations) {
    const dev = DEVELOPERS.find((d) => d.id === alloc.devId)!;
    const workerModel = alloc.workerModel ?? p.defaultWorker;
    const expertModel = alloc.expertModel ?? p.defaultExpert;
    const isOverride = Boolean(alloc.expertModel || alloc.workerModel);
    const rate = EXPERT_BLENDED_RATES[expertModel.id] ?? 0.005;

    const rand = mulberry32(p.id * 100000 + alloc.devId * 7919);
    const daily: DailyPoint[] = [];

    for (let i = 0; i < DAYS; i++) {
      const d = new Date(START.getTime() + i * 86400000);
      const dayOfWeek = d.getUTCDay();

      // Realistic weekday vs weekend engineering curve
      // Tuesday, Wednesday, Thursday are peak coding days
      let weekdayFactor = 1.0;
      if (dayOfWeek === 0) weekdayFactor = 0.12; // Sunday
      else if (dayOfWeek === 6) weekdayFactor = 0.20; // Saturday
      else if (dayOfWeek === 1) weekdayFactor = 0.90; // Monday sprint start
      else if (dayOfWeek === 2) weekdayFactor = 1.25; // Tuesday peak
      else if (dayOfWeek === 3) weekdayFactor = 1.30; // Wednesday peak
      else if (dayOfWeek === 4) weekdayFactor = 1.15; // Thursday testing/review
      else if (dayOfWeek === 5) weekdayFactor = 0.85; // Friday deploy/retro

      // Natural sprint cycle (14-day cadence with sprint ends)
      const sprintPhase = 0.9 + 0.2 * Math.sin((i / 14) * Math.PI);
      const dailyNoise = 0.88 + rand() * 0.24;

      // Realistic token metrics per dev per day:
      // Worker reads AST context: ~120k to 220k tokens/day
      // Expert synthesizes solution: ~16k to 35k tokens/day (~14% ratio)
      const baseRequests = 16 * alloc.weight * dev.baseActivity * 2.2;
      const requests = Math.max(1, Math.round(baseRequests * weekdayFactor * sprintPhase * dailyNoise));

      const workerTokensPerReq = 9500 + Math.round(rand() * 4500);
      const expertTokensPerReq = 1200 + Math.round(rand() * 800);

      const workerTokens = requests * workerTokensPerReq;
      const expertTokens = requests * expertTokensPerReq;

      // Real-world costs:
      // Actual cost = expertTokens * rate (Worker is $0 local/self-hosted)
      // Baseline cost = (workerTokens + expertTokens) * rate (if all context went to paid model)
      const cost = Math.round((expertTokens / 1000) * rate * 100) / 100;
      const baselineCost = Math.round(((workerTokens + expertTokens) / 1000) * rate * 100) / 100;
      const savings = Math.max(0, Math.round((baselineCost - cost) * 100) / 100);

      daily.push({
        day: isoDay(d),
        workerTokens,
        expertTokens,
        cost,
        baselineCost,
        savings,
        requests,
      });
    }

    ALL_MEMBER_STATS.push({
      projectId: p.id,
      devId: alloc.devId,
      workerModel,
      expertModel,
      isOverride,
      storiesAssigned: alloc.storiesAssigned,
      storiesDone: alloc.storiesDone,
      daily,
    });
  }
}

// ---------------------------------------------------------------------------
// Aggregation Utilities
// ---------------------------------------------------------------------------

function mergeDaily(pointsArray: DailyPoint[][]): DailyPoint[] {
  if (pointsArray.length === 0) return [];
  const map = new Map<string, DailyPoint>();

  for (const points of pointsArray) {
    for (const p of points) {
      const existing = map.get(p.day);
      if (!existing) {
        map.set(p.day, { ...p });
      } else {
        existing.workerTokens += p.workerTokens;
        existing.expertTokens += p.expertTokens;
        existing.cost = Math.round((existing.cost + p.cost) * 100) / 100;
        existing.baselineCost = Math.round((existing.baselineCost + p.baselineCost) * 100) / 100;
        existing.savings = Math.round((existing.savings + p.savings) * 100) / 100;
        existing.requests += p.requests;
      }
    }
  }

  return Array.from(map.values()).sort((a, b) => a.day.localeCompare(b.day));
}

function computeKpisFromDaily(daily: DailyPoint[], storiesAssigned: number, storiesDone: number, activeDevs: number): Kpis {
  const workerTokens = daily.reduce((acc, p) => acc + p.workerTokens, 0);
  const expertTokens = daily.reduce((acc, p) => acc + p.expertTokens, 0);
  const totalTokens = workerTokens + expertTokens;
  const expertCost = Math.round(daily.reduce((acc, p) => acc + p.cost, 0) * 100) / 100;
  const baselineCost = Math.round(daily.reduce((acc, p) => acc + p.baselineCost, 0) * 100) / 100;
  const savings = Math.max(0, Math.round((baselineCost - expertCost) * 100) / 100);
  const savingsPct = baselineCost > 0 ? Math.round((savings / baselineCost) * 1000) / 10 : 0;
  const requests = daily.reduce((acc, p) => acc + p.requests, 0);
  const costPerStory = storiesDone > 0 ? Math.round((expertCost / storiesDone) * 100) / 100 : null;

  return {
    totalTokens,
    workerTokens,
    expertTokens,
    workerCost: 0,
    expertCost,
    totalCost: expertCost,
    baselineCost,
    savings,
    savingsPct,
    requests,
    activeDevelopers: activeDevs,
    storiesAssigned,
    storiesDone,
    costPerStory,
  };
}

function computePreviousPeriod(currentDaily: DailyPoint[]): DailyPoint[] {
  // Previous 30-day baseline was ~18% lower adoption
  return currentDaily.map((p) => {
    const factor = 0.82;
    const workerTokens = Math.round(p.workerTokens * factor);
    const expertTokens = Math.round(p.expertTokens * factor);
    const cost = Math.round(p.cost * factor * 100) / 100;
    const baselineCost = Math.round(p.baselineCost * factor * 100) / 100;
    const savings = Math.round((baselineCost - cost) * 100) / 100;
    const requests = Math.round(p.requests * factor);
    return {
      ...p,
      workerTokens,
      expertTokens,
      cost,
      baselineCost,
      savings,
      requests,
    };
  });
}

function buildModelUsageBreakdown(memberStatsList: MemberDailyStats[]): ModelUsage[] {
  const modelMap = new Map<number, { model: ModelRef; tokens: number; cost: number; requests: number }>();

  for (const s of memberStatsList) {
    const wt = s.daily.reduce((acc, p) => acc + p.workerTokens, 0);
    const et = s.daily.reduce((acc, p) => acc + p.expertTokens, 0);
    const ec = s.daily.reduce((acc, p) => acc + p.cost, 0);
    const req = s.daily.reduce((acc, p) => acc + p.requests, 0);

    // Worker entry
    const wEntry = modelMap.get(s.workerModel.id) ?? { model: s.workerModel, tokens: 0, cost: 0, requests: 0 };
    wEntry.tokens += wt;
    wEntry.requests += req;
    modelMap.set(s.workerModel.id, wEntry);

    // Expert entry
    const eEntry = modelMap.get(s.expertModel.id) ?? { model: s.expertModel, tokens: 0, cost: 0, requests: 0 };
    eEntry.tokens += et;
    eEntry.cost = Math.round((eEntry.cost + ec) * 100) / 100;
    eEntry.requests += req;
    modelMap.set(s.expertModel.id, eEntry);
  }

  return Array.from(modelMap.values())
    .map((v) => ({
      modelId: v.model.id,
      model: v.model.name,
      provider: v.model.provider,
      tier: v.model.tier,
      tokens: v.tokens,
      cost: v.cost,
      requests: v.requests,
    }))
    .sort((a, b) => b.tokens - a.tokens);
}

// ---------------------------------------------------------------------------
// Rich Engineering Jira Issue Database
// ---------------------------------------------------------------------------

const JIRA_CATALOG: Record<string, { summary: string; category: JiraIssueRow['statusCategory']; status: string }[]> = {
  ANLYZR: [
    { summary: 'Optimize AST traversal cache for multi-module maven builds', category: 'DONE', status: 'Done' },
    { summary: 'Implement two-tier token compression for LLM context window', category: 'DONE', status: 'Done' },
    { summary: 'Benchmark Qwen 2.5 Coder 32B vs Gemma 2 on syntax parsing', category: 'DONE', status: 'Done' },
    { summary: 'Token budget circuit-breaker for IDE telemetry interceptor', category: 'DONE', status: 'Done' },
    { summary: 'Symbol reference graph indexing for incremental git diffs', category: 'DONE', status: 'Done' },
    { summary: 'Context extraction rules for Spring Boot 3.5 controller annotations', category: 'DONE', status: 'Done' },
    { summary: 'Fallback routing policy on worker inference timeout (>3s)', category: 'IN_PROGRESS', status: 'In Review' },
    { summary: 'IntelliJ plugin status bar token consumption widget', category: 'IN_PROGRESS', status: 'In Progress' },
    { summary: 'Telemetry payload compression via zstd stream', category: 'TODO', status: 'To Do' },
  ],
  ARCHDEP: [
    { summary: 'Automate Kubernetes Helm manifests for vLLM inference worker', category: 'DONE', status: 'Done' },
    { summary: 'Configure Horizontal Pod Autoscaler on prompt token queue depth', category: 'DONE', status: 'Done' },
    { summary: 'mTLS mutual authentication between IDE gateway and inference cluster', category: 'DONE', status: 'Done' },
    { summary: 'Terraform AWS Graviton4 GPU inference node group provisioner', category: 'DONE', status: 'Done' },
    { summary: 'Prometheus metrics exporter for worker latency percentiles (p95, p99)', category: 'DONE', status: 'Done' },
    { summary: 'Inference cache warming on git branch checkout webhook', category: 'IN_PROGRESS', status: 'In Review' },
    { summary: 'Multi-region failover policy for Claude API endpoints', category: 'TODO', status: 'To Do' },
  ],
  JSM: [
    { summary: 'Webhook receiver for Jira sprint transition events', category: 'DONE', status: 'Done' },
    { summary: 'Bi-directional link between IDE request eventId and Jira issue keys', category: 'DONE', status: 'Done' },
    { summary: 'Token usage and dollar cost attribution exporter for Jira stories', category: 'DONE', status: 'Done' },
    { summary: 'Real-time alert notification on project budget threshold (80%)', category: 'DONE', status: 'Done' },
    { summary: 'Jira Service Management dashboard widget integration', category: 'IN_PROGRESS', status: 'In Progress' },
    { summary: 'Export monthly audit report to Atlassian Confluence page', category: 'TODO', status: 'To Do' },
  ],
  CQE: [
    { summary: 'Automated unit test synthesis for edge cases in payment validation', category: 'DONE', status: 'Done' },
    { summary: 'Mutation testing runner to verify Claude-generated test suites', category: 'DONE', status: 'Done' },
    { summary: 'Benchmark coverage delta between raw Claude prompts vs MesterX worker', category: 'DONE', status: 'Done' },
    { summary: 'Assertion verification runner with Jest and JUnit XML reporter', category: 'DONE', status: 'Done' },
    { summary: 'Flaky test detector based on LLM temperature variance', category: 'IN_PROGRESS', status: 'In Review' },
    { summary: 'PR automated code review gate integration with GitHub Actions', category: 'TODO', status: 'To Do' },
  ],
  PLATFORM: [
    { summary: 'Organisation-level default model routing policy sync', category: 'DONE', status: 'Done' },
    { summary: 'High-throughput API key hashing and in-memory rate limiting', category: 'DONE', status: 'Done' },
    { summary: 'Database migration for multi-tier LLM token accounting schema', category: 'DONE', status: 'Done' },
    { summary: 'Session cookie security and role-based access control audit', category: 'DONE', status: 'Done' },
    { summary: 'Dynamic model catalog pricing sync with Anthropic and OpenAI APIs', category: 'IN_PROGRESS', status: 'In Progress' },
    { summary: 'OpenTelemetry distributed trace propagation across worker & expert tiers', category: 'TODO', status: 'To Do' },
  ],
};

function generateJiraIssues(projectKey: string, devDisplayName: string): JiraIssueRow[] {
  const catalog = JIRA_CATALOG[projectKey] ?? JIRA_CATALOG['ANLYZR'];
  return catalog.map((item, i) => ({
    key: `${projectKey}-${101 + i}`,
    summary: item.summary,
    status: item.status,
    statusCategory: item.category,
    assignee: devDisplayName,
    updatedAt: new Date(END.getTime() - (i * 1.5 + 0.5) * 86400000).toISOString(),
    resolvedAt: item.category === 'DONE' ? new Date(END.getTime() - (i * 2 + 1) * 86400000).toISOString() : null,
    url: `https://jira.mesterx.internal/browse/${projectKey}-${101 + i}`,
  }));
}

function generateUsageEvents(projectKey: string, devId: number, expertModel: ModelRef, workerModel: ModelRef): UsageEventRow[] {
  const rand = mulberry32(devId * 997 + projectKey.charCodeAt(0) * 101);
  const rate = EXPERT_BLENDED_RATES[expertModel.id] ?? 0.005;

  return Array.from({ length: 12 }, (_, i) => {
    const isWorkerOnly = rand() < 0.12;
    const workerTokens = Math.round(11000 + rand() * 18000);
    const expertTokens = isWorkerOnly ? 0 : Math.round(950 + rand() * 1400);
    const latencyWorker = Math.round(650 + rand() * 600);
    const latencyExpert = isWorkerOnly ? 0 : Math.round(750 + rand() * 950);
    const cost = isWorkerOnly ? 0 : Math.round((expertTokens / 1000) * rate * 10000) / 10000;
    const baselineCost = Math.round(((workerTokens + expertTokens) / 1000) * rate * 10000) / 10000;
    const savings = Math.round((baselineCost - cost) * 10000) / 10000;

    return {
      eventId: `ev_${projectKey.toLowerCase()}_${1000 + i}`,
      timestamp: new Date(END.getTime() - (i * 55 + Math.round(rand() * 20)) * 60000).toISOString(),
      projectKey,
      workerModel: workerModel.name,
      expertModel: isWorkerOnly ? null : expertModel.name,
      workerTokens,
      expertTokens,
      latencyMs: latencyWorker + latencyExpert,
      cost,
      savings,
      jiraKey: `${projectKey}-${101 + (i % 6)}`,
      outcome: isWorkerOnly ? 'WORKER_ONLY' : 'SUCCESS',
    };
  });
}

// ---------------------------------------------------------------------------
// Exported MOCK Controller
// ---------------------------------------------------------------------------

export const MOCK = {
  ALL_MODELS,
  WORKER_MODELS,
  EXPERT_MODELS,
  GLOBAL_WORKER: WORKER_MODELS[0],
  GLOBAL_EXPERT: EXPERT_MODELS[0],

  currentUser(role: CurrentUser['role']): CurrentUser {
    return {
      id: 1,
      email: 'admin@mesterx.io',
      displayName: 'Admin Leader',
      role,
      projects: PROJECTS_CONFIG.map((p) => ({
        id: p.id,
        key: p.key,
        name: p.name,
        roleInProject: 'MANAGER',
      })),
    };
  },

  overview(): Overview {
    // Sum across all allocations
    const allDaily = mergeDaily(ALL_MEMBER_STATS.map((s) => s.daily));
    const totalStoriesAssigned = ALL_MEMBER_STATS.reduce((acc, s) => acc + s.storiesAssigned, 0);
    const totalStoriesDone = ALL_MEMBER_STATS.reduce((acc, s) => acc + s.storiesDone, 0);

    const currentKpis = computeKpisFromDaily(allDaily, totalStoriesAssigned, totalStoriesDone, DEVELOPERS.length);
    const prevDaily = computePreviousPeriod(allDaily);
    const prevKpis = computeKpisFromDaily(prevDaily, Math.round(totalStoriesAssigned * 0.85), Math.round(totalStoriesDone * 0.83), DEVELOPERS.length);

    const byModel = buildModelUsageBreakdown(ALL_MEMBER_STATS);

    // Project summaries
    const projects: ProjectSummary[] = PROJECTS_CONFIG.map((p) => {
      const pStats = ALL_MEMBER_STATS.filter((s) => s.projectId === p.id);
      const pDaily = mergeDaily(pStats.map((s) => s.daily));
      const pStoriesAssigned = pStats.reduce((acc, s) => acc + s.storiesAssigned, 0);
      const pStoriesDone = pStats.reduce((acc, s) => acc + s.storiesDone, 0);
      const k = computeKpisFromDaily(pDaily, pStoriesAssigned, pStoriesDone, p.allocations.length);
      const budgetUsedPct = p.budgetUsd ? Math.round((k.totalCost / p.budgetUsd) * 1000) / 10 : null;

      return {
        id: p.id,
        key: p.key,
        name: p.name,
        developers: p.allocations.length,
        totalTokens: k.totalTokens,
        workerTokens: k.workerTokens,
        expertTokens: k.expertTokens,
        cost: k.totalCost,
        savings: k.savings,
        storiesAssigned: pStoriesAssigned,
        storiesDone: pStoriesDone,
        budgetUsd: p.budgetUsd,
        budgetUsedPct,
      };
    });

    // Top developers by cost
    const topDevelopers: DeveloperRow[] = DEVELOPERS.map((dev) => {
      const devStats = ALL_MEMBER_STATS.filter((s) => s.devId === dev.id);
      const devDaily = mergeDaily(devStats.map((s) => s.daily));
      const storiesAssigned = devStats.reduce((acc, s) => acc + s.storiesAssigned, 0);
      const storiesDone = devStats.reduce((acc, s) => acc + s.storiesDone, 0);
      const k = computeKpisFromDaily(devDaily, storiesAssigned, storiesDone, 1);

      return {
        userId: dev.id,
        displayName: dev.displayName,
        email: dev.email,
        workerTokens: k.workerTokens,
        expertTokens: k.expertTokens,
        cost: k.totalCost,
        savings: k.savings,
        requests: k.requests,
        storiesAssigned,
        storiesDone,
        costPerStory: k.costPerStory,
        override: dev.id === 103 ? { workerModel: WORKER_MODELS[2], expertModel: EXPERT_MODELS[1] } : null,
        lastActive: new Date(END.getTime() - (dev.id % 4) * 1800000).toISOString(),
      };
    }).sort((a, b) => b.cost - a.cost);

    return {
      kpis: { current: currentKpis, previous: prevKpis },
      daily: allDaily,
      byModel,
      projects,
      topDevelopers,
    };
  },

  projectDetail(id: number): ProjectDetail {
    const spec = PROJECTS_CONFIG.find((p) => p.id === id) ?? PROJECTS_CONFIG[0];
    const pStats = ALL_MEMBER_STATS.filter((s) => s.projectId === spec.id);
    const pDaily = mergeDaily(pStats.map((s) => s.daily));

    const pStoriesAssigned = pStats.reduce((acc, s) => acc + s.storiesAssigned, 0);
    const pStoriesDone = pStats.reduce((acc, s) => acc + s.storiesDone, 0);

    const currentKpis = computeKpisFromDaily(pDaily, pStoriesAssigned, pStoriesDone, spec.allocations.length);
    const prevDaily = computePreviousPeriod(pDaily);
    const prevKpis = computeKpisFromDaily(prevDaily, pStoriesAssigned - 3, pStoriesDone - 3, spec.allocations.length);

    const budgetUsedPct = spec.budgetUsd ? Math.round((currentKpis.totalCost / spec.budgetUsd) * 1000) / 10 : null;
    const budgetState = budgetUsedPct === null ? 'NONE' : budgetUsedPct >= 100 ? 'EXCEEDED' : budgetUsedPct >= 80 ? 'WARNING' : 'OK';

    const developers: DeveloperRow[] = spec.allocations.map((alloc) => {
      const s = pStats.find((item) => item.devId === alloc.devId)!;
      const dev = DEVELOPERS.find((d) => d.id === alloc.devId)!;
      const devKpis = computeKpisFromDaily(s.daily, s.storiesAssigned, s.storiesDone, 1);

      return {
        userId: dev.id,
        displayName: dev.displayName,
        email: dev.email,
        workerTokens: devKpis.workerTokens,
        expertTokens: devKpis.expertTokens,
        cost: devKpis.totalCost,
        savings: devKpis.savings,
        requests: devKpis.requests,
        storiesAssigned: s.storiesAssigned,
        storiesDone: s.storiesDone,
        costPerStory: devKpis.costPerStory,
        override: s.isOverride ? { workerModel: s.workerModel, expertModel: s.expertModel } : null,
        lastActive: new Date(END.getTime() - (dev.id % 5) * 1200000).toISOString(),
      };
    });

    return {
      project: {
        id: spec.id,
        key: spec.key,
        name: spec.name,
        jiraProjectKey: spec.jiraProjectKey,
        budgetUsd: spec.budgetUsd,
        alertPct: 80,
        budgetUsedUsd: currentKpis.totalCost,
        budgetUsedPct,
        budgetState,
        managers: spec.managers,
      },
      routing: {
        workerModel: spec.defaultWorker,
        expertModel: spec.defaultExpert,
        source: 'PROJECT',
        configVersion: 4,
      },
      kpis: { current: currentKpis, previous: prevKpis },
      daily: pDaily,
      byModel: buildModelUsageBreakdown(pStats),
      developers,
    };
  },

  projectMembers(projectId?: number): ProjectMemberRow[] {
    const list = projectId ? ALL_MEMBER_STATS.filter((s) => s.projectId === projectId) : ALL_MEMBER_STATS;

    return list.map((s) => {
      const p = PROJECTS_CONFIG.find((item) => item.id === s.projectId)!;
      const dev = DEVELOPERS.find((d) => d.id === s.devId)!;
      const k = computeKpisFromDaily(s.daily, s.storiesAssigned, s.storiesDone, 1);

      return {
        projectId: p.id,
        projectKey: p.key,
        projectName: p.name,
        userId: dev.id,
        displayName: dev.displayName,
        email: dev.email,
        workerModel: s.workerModel,
        expertModel: s.expertModel,
        isOverride: s.isOverride,
        cost: k.totalCost,
        savings: k.savings,
        requests: k.requests,
        storiesAssigned: s.storiesAssigned,
        storiesDone: s.storiesDone,
        costPerStory: k.costPerStory,
        lastActive: new Date(END.getTime() - (dev.id % 4) * 2400000).toISOString(),
      };
    });
  },

  developerDetail(projectId: number, userId: number): DeveloperDetail {
    const spec = PROJECTS_CONFIG.find((p) => p.id === projectId) ?? PROJECTS_CONFIG[0];
    const dev = DEVELOPERS.find((d) => d.id === userId) ?? DEVELOPERS[0];
    const stat = ALL_MEMBER_STATS.find((s) => s.projectId === spec.id && s.devId === dev.id) ?? ALL_MEMBER_STATS[0];

    const currentKpis = computeKpisFromDaily(stat.daily, stat.storiesAssigned, stat.storiesDone, 1);
    const prevDaily = computePreviousPeriod(stat.daily);
    const prevKpis = computeKpisFromDaily(prevDaily, stat.storiesAssigned - 2, stat.storiesDone - 2, 1);

    return {
      user: { id: dev.id, displayName: dev.displayName, email: dev.email, role: 'DEVELOPER' },
      project: { id: spec.id, key: spec.key, name: spec.name },
      routing: {
        workerModel: stat.workerModel,
        expertModel: stat.expertModel,
        source: stat.isOverride ? 'USER' : 'PROJECT',
        configVersion: 4,
      },
      kpis: { current: currentKpis, previous: prevKpis },
      daily: stat.daily,
      byModel: buildModelUsageBreakdown([stat]),
      events: {
        content: generateUsageEvents(spec.key, dev.id, stat.expertModel, stat.workerModel),
        page: 0,
        size: 12,
        totalElements: currentKpis.requests,
        totalPages: Math.ceil(currentKpis.requests / 12),
      },
      jiraIssues: generateJiraIssues(spec.key, dev.displayName),
    };
  },

  meUsage(): DeveloperDetail {
    return this.developerDetail(1, 101);
  },

  projectSummaries(): ProjectSummary[] {
    return this.overview().projects;
  },

  adminUsers(): AdminUser[] {
    return DEVELOPERS.map((d, i) => {
      const devProjects = PROJECTS_CONFIG.filter((p) => p.allocations.some((a) => a.devId === d.id));
      return {
        id: d.id,
        email: d.email,
        displayName: d.displayName,
        role: 'DEVELOPER',
        status: 'ACTIVE',
        jiraAccountId: `jira_acc_${d.displayName.toLowerCase().replace(/[^a-z]/g, '')}`,
        lastSeen: new Date(END.getTime() - i * 4200000).toISOString(),
        projects: devProjects.map((p) => ({
          projectId: p.id,
          key: p.key,
          name: p.name,
          roleInProject: 'MEMBER',
        })),
        apiKeys: [
          {
            id: d.id * 10 + 1,
            label: 'IntelliJ IDEA Plugin — Primary',
            prefix: `mx_live_${d.displayName.slice(0, 2).toLowerCase()}${d.id}`,
            createdAt: '2026-08-15T00:00:00Z',
            revokedAt: null,
            lastUsedAt: new Date(END.getTime() - i * 1800000).toISOString(),
          },
          {
            id: d.id * 10 + 2,
            label: 'VS Code Extension — Remote Dev',
            prefix: `mx_live_vscode_${d.id}`,
            createdAt: '2026-09-01T00:00:00Z',
            revokedAt: null,
            lastUsedAt: new Date(END.getTime() - (i + 4) * 3600000).toISOString(),
          },
        ],
      };
    });
  },

  adminProjects(): AdminProject[] {
    return PROJECTS_CONFIG.map((p) => ({
      id: p.id,
      key: p.key,
      name: p.name,
      jiraProjectKey: p.jiraProjectKey,
      budgetUsd: p.budgetUsd,
      alertPct: 80,
      memberCount: p.allocations.length,
      managers: p.managers.map((m) => m.displayName),
    }));
  },

  audit(): AuditEntry[] {
    return [
      {
        id: 1,
        timestamp: new Date(END.getTime() - 45 * 60000).toISOString(),
        actor: 'Priya Mehta (Lead Architect)',
        action: 'UPDATE_ROUTING',
        entity: 'routing',
        entityId: 'PROJECT:1 (Analyser)',
        before: { workerModel: 'DeepSeek Coder V2', expertModel: 'Claude Opus 5.5' },
        after: { workerModel: 'Qwen 2.5 Coder 32B', expertModel: 'Claude Sonnet 5.5' },
      },
      {
        id: 2,
        timestamp: new Date(END.getTime() - 180 * 60000).toISOString(),
        actor: 'Rajesh Iyer (DevOps Lead)',
        action: 'UPDATE_BUDGET',
        entity: 'project',
        entityId: 'PROJECT:2 (Architecture Deployment)',
        before: { budgetUsd: 600 },
        after: { budgetUsd: 900 },
      },
      {
        id: 3,
        timestamp: new Date(END.getTime() - 86400000).toISOString(),
        actor: 'Priya Mehta (Lead Architect)',
        action: 'SET_USER_OVERRIDE',
        entity: 'routing',
        entityId: 'USER:103 (Yashwant)',
        before: null,
        after: { workerModel: 'Gemma 2 27B', expertModel: 'Claude Opus 5.5' },
      },
      {
        id: 4,
        timestamp: new Date(END.getTime() - 2 * 86400000).toISOString(),
        actor: 'Admin Leader',
        action: 'REGISTER_MODEL',
        entity: 'model',
        entityId: 'MODEL:1 (Qwen 2.5 Coder 32B)',
        before: null,
        after: { endpoint: 'http://vllm-cluster.internal:8000', provider: 'Alibaba (Self-hosted)' },
      },
      {
        id: 5,
        timestamp: new Date(END.getTime() - 4 * 86400000).toISOString(),
        actor: 'Admin Leader',
        action: 'CREATE_PROJECT',
        entity: 'project',
        entityId: 'PROJECT:5 (Platform Core)',
        before: null,
        after: { key: 'PLATFORM', budgetUsd: 2000, managers: ['Priya Mehta', 'Rajesh Iyer'] },
      },
    ];
  },

  models(): Model[] {
    return ALL_MODELS;
  },
};
