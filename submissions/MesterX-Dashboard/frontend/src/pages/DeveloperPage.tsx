import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Coins, TrendingUp, Layers, Activity } from 'lucide-react';
import { useDeveloper, useMyUsage } from '../api/hooks';
import { KpiTile } from '../components/KpiTile';
import { DataTable, type Column } from '../components/DataTable';
import { TokensStackedArea } from '../components/charts';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { StatusBadge, TierBadge } from '../components/Badge';
import { formatTokens, formatUsd, formatInt, formatDateTime, formatMs } from '../lib/format';
import type { JiraIssueRow, UsageEventRow } from '../api/types';

export function DeveloperPage() {
  const { id, userId } = useParams<{ id: string; userId: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useDeveloper(Number(id), Number(userId));
  return <DeveloperDetailView data={data} isLoading={isLoading} isError={isError} error={error} refetch={refetch} backTo={() => navigate(`/projects/${id}`)} backLabel="Back to project" />;
}

export function MyUsagePage() {
  const { data, isLoading, isError, error, refetch } = useMyUsage();
  return <DeveloperDetailView data={data} isLoading={isLoading} isError={isError} error={error} refetch={refetch} />;
}

function DeveloperDetailView({
  data,
  isLoading,
  isError,
  error,
  refetch,
  backTo,
  backLabel = 'Overview',
}: {
  data: import('../api/types').DeveloperDetail | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
  backTo?: () => void;
  backLabel?: string;
}) {
  if (isLoading) return <div className="page"><SkeletonBlock rows={6} /></div>;
  if (isError || !data) return <div className="page"><ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={refetch} /></div>;

  const { user, project, routing, kpis, daily, events, jiraIssues } = data;
  const c = kpis.current;
  const p = kpis.previous;

  const eventCols: Column<UsageEventRow>[] = [
    { key: 'timestamp', header: 'Time', sortValue: (r) => r.timestamp, render: (r) => <span className="tnum subtle">{formatDateTime(r.timestamp)}</span> },
    { key: 'workerModel', header: 'Worker', render: (r) => <span>{r.workerModel}</span> },
    { key: 'expertModel', header: 'Expert', render: (r) => (r.expertModel ? r.expertModel : <span className="subtle">—</span>) },
    { key: 'workerTokens', header: 'Worker tok', align: 'right', sortValue: (r) => r.workerTokens, render: (r) => <span className="tnum">{formatTokens(r.workerTokens)}</span> },
    { key: 'expertTokens', header: 'Expert tok', align: 'right', sortValue: (r) => r.expertTokens, render: (r) => <span className="tnum">{formatTokens(r.expertTokens)}</span> },
    { key: 'latencyMs', header: 'Latency', align: 'right', sortValue: (r) => r.latencyMs, render: (r) => <span className="tnum">{formatMs(r.latencyMs)}</span> },
    { key: 'cost', header: 'Cost', align: 'right', sortValue: (r) => r.cost, render: (r) => <span className="tnum">{formatUsd(r.cost)}</span> },
    { key: 'jiraKey', header: 'Jira', render: (r) => (r.jiraKey ? <span className="mono">{r.jiraKey}</span> : <span className="subtle">—</span>) },
    { key: 'outcome', header: 'Outcome', render: (r) => <StatusBadge status={r.outcome} /> },
  ];

  const issueCols: Column<JiraIssueRow>[] = [
    { key: 'key', header: 'Key', render: (r) => <span className="mono">{r.key}</span> },
    { key: 'summary', header: 'Summary', render: (r) => <span>{r.summary}</span> },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.statusCategory} /> },
    { key: 'updatedAt', header: 'Updated', align: 'right', sortValue: (r) => r.updatedAt, render: (r) => <span className="tnum subtle">{formatDateTime(r.updatedAt)}</span> },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          {backTo && (
            <button className="back-link" onClick={backTo}>
              <ArrowLeft size={14} /> {backLabel}
            </button>
          )}
          <h1>{user.displayName}</h1>
          <p className="subtle">{user.email}{project ? ` · ${project.name}` : ' · all projects'}</p>
        </div>
      </div>

      <div className="routing-bar">
        <div className="routing-model"><TierBadge tier="WORKER" /><span className="routing-name">{routing.workerModel.name}</span></div>
        <span className="routing-arrow">→</span>
        <div className="routing-model"><TierBadge tier="EXPERT" /><span className="routing-name">{routing.expertModel.name}</span></div>
      </div>

      <div className="kpi-grid">
        <KpiTile label="Total tokens" value={formatTokens(c.totalTokens)} delta={{ current: c.totalTokens, previous: p.totalTokens }} icon={<Layers size={16} />} />
        <KpiTile label="Cost" value={formatUsd(c.totalCost)} delta={{ current: c.totalCost, previous: p.totalCost, goodWhen: 'down' }} icon={<Coins size={16} />} />
        <KpiTile label="Est. savings" value={formatUsd(c.savings)} accent delta={{ current: c.savings, previous: p.savings }} icon={<TrendingUp size={16} />} help="Baseline (paid-only) cost minus actual cost." />
        <KpiTile label="Requests" value={formatInt(c.requests)} delta={{ current: c.requests, previous: p.requests }} icon={<Activity size={16} />} />
        <KpiTile label="Stories" value={`${c.storiesDone}/${c.storiesAssigned}`} delta={{ current: c.storiesDone, previous: p.storiesDone }} />
        <KpiTile label="Cost/story saved" value={c.storiesDone > 0 ? `+${formatUsd(c.savings / c.storiesDone)}` : '—'} accent help="Estimated token cost savings achieved per completed Jira story." />
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-head"><h2>Daily tokens</h2></div>
          <TokensStackedArea data={daily} />
        </section>
        <section className="card">
          <div className="card-head"><h2>Jira stories</h2></div>
          <DataTable columns={issueCols} rows={jiraIssues} rowKey={(r) => r.key} />
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Request log</h2>
          <span className="subtle">Metadata only — no code or prompts are stored.</span>
        </div>
        <DataTable columns={eventCols} rows={events.content} rowKey={(r) => r.eventId} />
      </section>
    </div>
  );
}