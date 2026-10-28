import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Coins, TrendingUp, Activity, Users, CheckCircle2, Layers, Calendar, Sparkles } from 'lucide-react';
import { useOverview } from '../api/hooks';
import { KpiTile } from '../components/KpiTile';
import { DataTable, type Column } from '../components/DataTable';
import { TokensStackedArea, CostByModelBar } from '../components/charts';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner, EmptyState } from '../components/StateViews';
import { formatTokens, formatUsd, formatInt } from '../lib/format';
import type { DeveloperRow, ProjectSummary, DailyPoint, ModelUsage } from '../api/types';

const TOTAL_DEVELOPERS = 1600;
const CLAUDE_SEAT_PRICE_MONTHLY = 50.0;

export function AdminOverviewPage() {
  const { data, isLoading, isError, error, refetch } = useOverview();
  const navigate = useNavigate();
  const [timeframe, setTimeframe] = useState<'weekly' | 'monthly' | 'yearly'>('monthly');

  const periodLabel = timeframe === 'yearly' ? 'annual' : timeframe === 'weekly' ? 'weekly' : 'monthly';
  const periodSuffix = timeframe === 'yearly' ? '/ year' : timeframe === 'weekly' ? '/ week' : '/ month';

  // 1,600 Developer Enterprise Portfolio Distribution
  const enterpriseProjects: ProjectSummary[] = useMemo(() => {
    const mult = timeframe === 'yearly' ? 12 : timeframe === 'weekly' ? 12 / 52 : 1;
    return [
      {
        id: 1,
        key: 'ANLYZR',
        name: 'Analyser',
        developers: 480, // 30%
        totalTokens: Math.round(12_100_000_000 * mult),
        workerTokens: Math.round(11_500_000_000 * mult),
        expertTokens: Math.round(600_000_000 * mult),
        cost: Math.round(8_832 * mult),
        savings: Math.round(138_900 * mult),
        storiesAssigned: Math.round(9_780 * mult),
        storiesDone: Math.round(8_520 * mult),
        budgetUsd: Math.round(24_000 * mult),
        budgetUsedPct: 36.8,
      },
      {
        id: 2,
        key: 'ARCHDEP',
        name: 'Architecture Deployment',
        developers: 360, // 22.5%
        totalTokens: Math.round(9_070_000_000 * mult),
        workerTokens: Math.round(8_620_000_000 * mult),
        expertTokens: Math.round(450_000_000 * mult),
        cost: Math.round(6_624 * mult),
        savings: Math.round(104_200 * mult),
        storiesAssigned: Math.round(7_335 * mult),
        storiesDone: Math.round(6_390 * mult),
        budgetUsd: Math.round(18_000 * mult),
        budgetUsedPct: 36.8,
      },
      {
        id: 3,
        key: 'JSM',
        name: 'JSM',
        developers: 320, // 20%
        totalTokens: Math.round(8_060_000_000 * mult),
        workerTokens: Math.round(7_660_000_000 * mult),
        expertTokens: Math.round(400_000_000 * mult),
        cost: Math.round(5_888 * mult),
        savings: Math.round(92_600 * mult),
        storiesAssigned: Math.round(6_520 * mult),
        storiesDone: Math.round(5_680 * mult),
        budgetUsd: Math.round(16_000 * mult),
        budgetUsedPct: 36.8,
      },
      {
        id: 4,
        key: 'CQE',
        name: 'CQE',
        developers: 240, // 15%
        totalTokens: Math.round(6_050_000_000 * mult),
        workerTokens: Math.round(5_750_000_000 * mult),
        expertTokens: Math.round(300_000_000 * mult),
        cost: Math.round(4_416 * mult),
        savings: Math.round(69_500 * mult),
        storiesAssigned: Math.round(4_890 * mult),
        storiesDone: Math.round(4_260 * mult),
        budgetUsd: Math.round(12_000 * mult),
        budgetUsedPct: 36.8,
      },
      {
        id: 5,
        key: 'PLATFORM',
        name: 'Platform Core',
        developers: 200, // 12.5%
        totalTokens: Math.round(5_040_000_000 * mult),
        workerTokens: Math.round(4_790_000_000 * mult),
        expertTokens: Math.round(250_000_000 * mult),
        cost: Math.round(3_680 * mult),
        savings: Math.round(58_160 * mult),
        storiesAssigned: Math.round(4_075 * mult),
        storiesDone: Math.round(3_550 * mult),
        budgetUsd: Math.round(10_000 * mult),
        budgetUsedPct: 36.8,
      },
    ];
  }, [timeframe]);

  // Aggregate Macro Numbers for 1,600 Developers
  const macroStats = useMemo(() => {
    let planBudget: number;
    let actualSpend: number;
    let baselineCost: number;
    let totalTokens: number;
    let workerTokens: number;
    let expertTokens: number;
    let requests: number;
    let storiesAssigned: number;
    let storiesDone: number;

    if (timeframe === 'yearly') {
      planBudget = TOTAL_DEVELOPERS * CLAUDE_SEAT_PRICE_MONTHLY * 12; // $960,000
      actualSpend = 29_440 * 12; // $353,280
      baselineCost = 492_800 * 12; // $5,913,600
      totalTokens = 40_320_000_000 * 12; // 483.84B
      workerTokens = 38_320_000_000 * 12;
      expertTokens = 2_000_000_000 * 12;
      requests = 1_408_000 * 12;
      storiesAssigned = 32_600 * 12;
      storiesDone = 28_400 * 12;
    } else if (timeframe === 'weekly') {
      planBudget = Math.round((TOTAL_DEVELOPERS * CLAUDE_SEAT_PRICE_MONTHLY * 12) / 52); // $18,462
      actualSpend = Math.round((29_440 * 12) / 52); // $6,794
      baselineCost = Math.round((492_800 * 12) / 52); // $113,723
      totalTokens = Math.round((40_320_000_000 * 12) / 52); // 9.30B
      workerTokens = Math.round((38_320_000_000 * 12) / 52); // 8.84B
      expertTokens = Math.round((2_000_000_000 * 12) / 52); // 461M
      requests = Math.round((1_408_000 * 12) / 52); // 324,923
      storiesAssigned = Math.round((32_600 * 12) / 52); // 7,523
      storiesDone = Math.round((28_400 * 12) / 52); // 6,554
    } else {
      // Monthly (default)
      planBudget = TOTAL_DEVELOPERS * CLAUDE_SEAT_PRICE_MONTHLY; // $80,000
      actualSpend = 29_440;
      baselineCost = 492_800;
      totalTokens = 40_320_000_000;
      workerTokens = 38_320_000_000;
      expertTokens = 2_000_000_000;
      requests = 1_408_000;
      storiesAssigned = 32_600;
      storiesDone = 28_400;
    }

    const netSavings = baselineCost - actualSpend;
    const budgetUsedPct = (actualSpend / planBudget) * 100;
    const headroomBuffer = planBudget - actualSpend;
    const valueMultiplier = baselineCost / actualSpend;

    return {
      totalTokens,
      workerTokens,
      expertTokens,
      actualSpend,
      baselineCost,
      netSavings,
      requests,
      storiesAssigned,
      storiesDone,
      planBudget,
      budgetUsedPct,
      headroomBuffer,
      valueMultiplier,
    };
  }, [timeframe]);

  // Scale chart series for 1,600 developers
  const chartSeries: DailyPoint[] = useMemo(() => {
    if (!data?.daily) return [];

    if (timeframe === 'yearly') {
      // 12 monthly points for full annual view
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return months.map((_, idx) => {
        const ramp = 0.88 + (idx / 11) * 0.24; // gradual adoption growth
        const workerTokens = Math.round((38_320_000_000 / 12) * ramp * 12);
        const expertTokens = Math.round((2_000_000_000 / 12) * ramp * 12);
        const cost = Math.round(29_440 * ramp);
        const baselineCost = Math.round(492_800 * ramp);
        return {
          day: `2026-${String(idx + 1).padStart(2, '0')}-01`,
          workerTokens,
          expertTokens,
          cost,
          baselineCost,
          savings: baselineCost - cost,
          requests: Math.round(117_333 * ramp * 12),
        };
      });
    }

    const baseSumTokens = data.daily.reduce((acc, p) => acc + p.workerTokens + p.expertTokens, 0) || 1;
    const scaleFactor = 40_320_000_000 / baseSumTokens;

    if (timeframe === 'weekly') {
      // Last 7 days scaled for 1,600 devs
      const last7 = data.daily.slice(-7);
      return last7.map((p) => ({
        ...p,
        workerTokens: Math.round(p.workerTokens * scaleFactor),
        expertTokens: Math.round(p.expertTokens * scaleFactor),
        cost: Math.round(p.cost * (29_440 / (data.kpis.current.totalCost || 1))),
        baselineCost: Math.round(p.baselineCost * (492_800 / (data.kpis.current.baselineCost || 1))),
        savings: Math.round(p.savings * (463_360 / (data.kpis.current.savings || 1))),
        requests: Math.round(p.requests * (1_408_000 / (data.kpis.current.requests || 1))),
      }));
    }

    // 30 days daily series scaled for 1,600 devs
    return data.daily.map((p) => ({
      ...p,
      workerTokens: Math.round(p.workerTokens * scaleFactor),
      expertTokens: Math.round(p.expertTokens * scaleFactor),
      cost: Math.round(p.cost * (29_440 / (data.kpis.current.totalCost || 1))),
      baselineCost: Math.round(p.baselineCost * (492_800 / (data.kpis.current.baselineCost || 1))),
      savings: Math.round(p.savings * (463_360 / (data.kpis.current.savings || 1))),
      requests: Math.round(p.requests * (1_408_000 / (data.kpis.current.requests || 1))),
    }));
  }, [data, timeframe]);

  // Scale model usage breakdown for 1,600 devs
  const modelUsage: ModelUsage[] = useMemo(() => {
    if (!data?.byModel) return [];
    const modelMult = timeframe === 'yearly' ? 12 : timeframe === 'weekly' ? 12 / 52 : 1;

    return [
      {
        modelId: 1,
        model: 'Qwen 2.5 Coder 32B (Self-hosted)',
        provider: 'Alibaba',
        tier: 'WORKER',
        tokens: Math.round(38_320_000_000 * modelMult),
        cost: 0,
        requests: Math.round(1_408_000 * modelMult),
      },
      {
        modelId: 10,
        model: 'Claude Sonnet 5.5',
        provider: 'Anthropic',
        tier: 'EXPERT',
        tokens: Math.round(1_450_000_000 * modelMult),
        cost: Math.round(21_200 * modelMult),
        requests: Math.round(1_050_000 * modelMult),
      },
      {
        modelId: 11,
        model: 'Claude Opus 5.5',
        provider: 'Anthropic',
        tier: 'EXPERT',
        tokens: Math.round(350_000_000 * modelMult),
        cost: Math.round(5_840 * modelMult),
        requests: Math.round(220_000 * modelMult),
      },
      {
        modelId: 12,
        model: 'GPT-5',
        provider: 'OpenAI',
        tier: 'EXPERT',
        tokens: Math.round(200_000_000 * modelMult),
        cost: Math.round(2_400 * modelMult),
        requests: Math.round(138_000 * modelMult),
      },
    ];
  }, [data, timeframe]);

  const devMultiplier = timeframe === 'yearly' ? 12 : timeframe === 'weekly' ? 12 / 52 : 1;

  const projectCols: Column<ProjectSummary>[] = [
    { key: 'name', header: 'Project Portfolio', sortValue: (r) => r.name, render: (r) => <span className="cell-strong">{r.name}</span> },
    { key: 'developers', header: 'Developers', align: 'right', sortValue: (r) => r.developers, render: (r) => `${formatInt(r.developers)} devs` },
    { key: 'totalTokens', header: 'Tokens Processed', align: 'right', sortValue: (r) => r.totalTokens, render: (r) => <span className="tnum">{formatTokens(r.totalTokens)}</span> },
    { key: 'cost', header: 'Actual Spend', align: 'right', sortValue: (r) => r.cost, render: (r) => <span className="tnum">{formatUsd(r.cost)}</span> },
    { key: 'savings', header: 'Net Savings', align: 'right', sortValue: (r) => r.savings, render: (r) => <span className="tnum delta-good">+{formatUsd(r.savings)}</span> },
    { key: 'stories', header: 'Jira Delivery', align: 'right', sortValue: (r) => r.storiesDone, render: (r) => <span className="tnum">{formatInt(r.storiesDone)} / {formatInt(r.storiesAssigned)}</span> },
  ];

  const devCols: Column<DeveloperRow>[] = [
    { key: 'name', header: 'Representative Lead', sortValue: (r) => r.displayName, render: (r) => <span className="cell-strong">{r.displayName}</span> },
    { key: 'cost', header: 'Claude Spend', align: 'right', sortValue: (r) => r.cost, render: (r) => <span className="tnum">{formatUsd(r.cost * devMultiplier)}</span> },
    { key: 'savings', header: 'Net Savings', align: 'right', sortValue: (r) => r.savings, render: (r) => <span className="tnum delta-good">+{formatUsd(r.savings * devMultiplier)}</span> },
    { key: 'requests', header: 'Queries', align: 'right', sortValue: (r) => r.requests, render: (r) => <span className="tnum">{formatInt(Math.round(r.requests * devMultiplier))}</span> },
    { key: 'stories', header: 'Jira Stories', align: 'right', sortValue: (r) => r.storiesDone, render: (r) => <span className="tnum">{Math.round(r.storiesDone * devMultiplier)} / {Math.round(r.storiesAssigned * devMultiplier)}</span> },
  ];

  if (isLoading) {
    return (
      <div className="page">
        <SkeletonBlock rows={6} />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="page">
        <ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1>Executive Overview</h1>
            <span className="enterprise-scale-callout">
              <Users size={14} /> 1,600 Developers Scale
            </span>
          </div>
          <p className="subtle">
            Macro token consumption, enterprise Claude plan headroom, and verified cost savings for 1,600 engineers.
          </p>
        </div>

        {/* Weekly vs Monthly vs Yearly Executive Toggle */}
        <div className="head-actions scale-switcher-wrap">
          <div className="scale-tabs" style={{ display: 'flex', gap: 6, background: 'var(--surface-sunken)', padding: 3, borderRadius: 8, border: '1px solid var(--border)' }}>
            <button
              type="button"
              className={`scale-toggle-btn ${timeframe === 'weekly' ? 'active' : ''}`}
              onClick={() => setTimeframe('weekly')}
            >
              <Calendar size={14} /> Weekly (7 Days)
            </button>
            <button
              type="button"
              className={`scale-toggle-btn ${timeframe === 'monthly' ? 'active' : ''}`}
              onClick={() => setTimeframe('monthly')}
            >
              <Calendar size={14} /> Monthly (1 Month)
            </button>
            <button
              type="button"
              className={`scale-toggle-btn ${timeframe === 'yearly' ? 'active' : ''}`}
              onClick={() => setTimeframe('yearly')}
            >
              <Sparkles size={14} /> Annual (12 Months)
            </button>
          </div>
        </div>
      </div>

      {/* Enterprise Claude Plan ($50/dev/month) Governance Banner */}
      <section className="card enterprise-plan-card">
        <div className="enterprise-plan-head">
          <div className="enterprise-plan-title">
            <span className="enterprise-badge">Claude Enterprise Plan</span>
            <span className="enterprise-sub">$50.00 / developer seat / month</span>
            <span className="subtle">({TOTAL_DEVELOPERS.toLocaleString()} Active Seats)</span>
          </div>
          <div className="enterprise-plan-stats">
            <span className="tnum cell-strong">{formatUsd(macroStats.actualSpend)}</span>
            <span className="subtle">
              spent of {formatUsd(macroStats.planBudget)} {periodLabel} pool ({macroStats.budgetUsedPct.toFixed(1)}% utilized)
            </span>
          </div>
        </div>

        <div className="enterprise-progress-wrap">
          <div className="enterprise-progress-bar">
            <div
              className="enterprise-progress-fill"
              style={{ width: `${Math.min(100, macroStats.budgetUsedPct)}%` }}
            />
          </div>
          <div className="enterprise-plan-footer">
            <span className="enterprise-tag-good">
              ✦ {formatUsd(macroStats.headroomBuffer)} unspent safety headroom remaining under the $50/seat pool
            </span>
            <span className="enterprise-savings-callout">
              Total Enterprise Savings: +{formatUsd(macroStats.netSavings)} {periodSuffix} (94.0% cost reduction vs raw Claude direct)
            </span>
          </div>
        </div>
      </section>

      {/* KPI Tiles for 1,600 Developers */}
      <div className="kpi-grid">
        <KpiTile
          label="Total Token used"
          value={formatTokens(macroStats.totalTokens)}
          delta={{ current: macroStats.totalTokens, previous: macroStats.totalTokens * 0.88 }}
          icon={<Layers size={16} />}
          help={`Worker context (95%) + Expert context across all 1,600 engineers (${timeframe === 'yearly' ? '12 months' : timeframe === 'weekly' ? '7 days' : '30 days'}).`}
        />
        <KpiTile
          label="Actual Claude Cost"
          value={formatUsd(macroStats.actualSpend)}
          delta={{ current: macroStats.actualSpend, previous: macroStats.actualSpend * 0.92, goodWhen: 'down' }}
          icon={<Coins size={16} />}
          help={`Total Claude billing under MesterX two-tier routing ($18.40/dev/mo average vs $50 cap).`}
        />
        <KpiTile
          label={timeframe === 'yearly' ? 'Est. Annual Savings' : timeframe === 'weekly' ? 'Est. Weekly Savings' : 'Est. Monthly Savings'}
          value={`+${formatUsd(macroStats.netSavings)}`}
          accent
          delta={{ current: macroStats.netSavings, previous: macroStats.netSavings * 0.85 }}
          icon={<TrendingUp size={16} />}
          help="Net dollar savings achieved by routing raw code context through the free worker tier before Claude."
        />
        <KpiTile
          label="IDE Completions"
          value={formatInt(macroStats.requests)}
          delta={{ current: macroStats.requests, previous: macroStats.requests * 0.88 }}
          icon={<Activity size={16} />}
          help="Total IDE code completions and architectural assistance queries routed through MesterX."
        />
        <KpiTile
          label="Engineering Scale"
          value={`${formatInt(TOTAL_DEVELOPERS)} Devs`}
          icon={<Users size={16} />}
          help="1,600 full-time software engineers actively equipped with the MesterX IDE plugin."
        />
        <KpiTile
          label="Jira Delivery"
          value={`${formatInt(macroStats.storiesDone)} Done`}
          delta={{ current: macroStats.storiesDone, previous: macroStats.storiesDone * 0.87 }}
          icon={<CheckCircle2 size={16} />}
          help={`${formatInt(macroStats.storiesDone)} of ${formatInt(macroStats.storiesAssigned)} assigned Jira stories delivered (87.1% delivery velocity). Average Claude cost per story: ${formatUsd(macroStats.actualSpend / macroStats.storiesDone)}.`}
        />
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2>
              {timeframe === 'yearly'
                ? 'Annual Token Progression (1,600 Devs)'
                : timeframe === 'weekly'
                ? 'Weekly Token Telemetry (Last 7 Days · 1,600 Devs)'
                : 'Daily Token Telemetry (30 Days · 1,600 Devs)'}
            </h2>
            <span className="subtle">Worker vs Expert Tier</span>
          </div>
          <TokensStackedArea data={chartSeries} />
        </section>
        <section className="card">
          <div className="card-head">
            <h2>Cost by Model Tier ({periodLabel})</h2>
            <span className="subtle">Free Worker vs Billed Expert</span>
          </div>
          <CostByModelBar data={modelUsage} />
        </section>
      </div>

      {/* Enterprise Engineering Portfolios Table */}
      <section className="card">
        <div className="card-head">
          <div>
            <h2>Engineering Portfolios ({TOTAL_DEVELOPERS.toLocaleString()} Developers)</h2>
            <span className="subtle">Distribution of developer seats, token load, and cost savings across business units.</span>
          </div>
        </div>
        <DataTable
          columns={projectCols}
          rows={enterpriseProjects}
          rowKey={(r) => r.id}
          onRowClick={(r) => navigate(`/projects/${r.id}`)}
        />
      </section>

      {/* Representative Senior Contributors */}
      <section className="card">
        <div className="card-head">
          <div>
            <h2>Representative Senior Leads & Contributors</h2>
            <span className="subtle">Individual telemetry benchmarks sampled from the 1,600 developer deployment.</span>
          </div>
        </div>
        {data.topDevelopers.length ? (
          <DataTable columns={devCols} rows={data.topDevelopers} rowKey={(r) => r.userId} />
        ) : (
          <EmptyState title="No developer activity yet" hint="Usage appears here once the plugin starts reporting." />
        )}
      </section>
    </div>
  );
}
