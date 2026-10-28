import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Download, Pencil, ArrowLeft, Coins, TrendingUp, Layers, Users, CheckCircle2 } from 'lucide-react';
import { useProject, useModels } from '../api/hooks';
import { KpiTile } from '../components/KpiTile';
import { DataTable, type Column } from '../components/DataTable';
import { TokensStackedArea, CostLineChart, CostPerStoryBar } from '../components/charts';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { Select } from '../components/Select';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { TierBadge } from '../components/Badge';
import { formatTokens, formatUsd, formatInt } from '../lib/format';
import type { DeveloperRow, ModelRef } from '../api/types';

export function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useProject(projectId);
  const { data: models } = useModels();

  const [showRouting, setShowRouting] = useState(false);

  if (isLoading) {
    return <div className="page"><SkeletonBlock rows={6} /></div>;
  }
  if (isError || !data) {
    return <div className="page"><ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={() => refetch()} /></div>;
  }

  const { project, routing, kpis, daily, developers } = data;
  const c = kpis.current;
  const p = kpis.previous;

  const workerModels = (models ?? []).filter((m) => m.tier === 'WORKER' && m.enabled);
  const expertModels = (models ?? []).filter((m) => m.tier === 'EXPERT' && m.enabled);

  const cols: Column<DeveloperRow>[] = [
    {
      key: 'name',
      header: 'Developer',
      sortValue: (r) => r.displayName,
      render: (r) => {
        const initials = r.displayName
          .split(' ')
          .map((n) => n[0])
          .slice(0, 2)
          .join('')
          .toUpperCase();
        return (
          <div className="member-cell">
            <div className="avatar">{initials}</div>
            <div className="member-info">
              <span className="member-name">{r.displayName}</span>
              <span className="member-email">{r.email}</span>
            </div>
          </div>
        );
      },
    },
    {
      key: 'workerModel',
      header: 'Worker Model',
      sortValue: (r) => (r.override ? r.override.workerModel.name : routing.workerModel.name),
      render: (r) => {
        const model = r.override ? r.override.workerModel : routing.workerModel;
        return (
          <div className="model-cell">
            <div className="model-title-wrap">
              <TierBadge tier="WORKER" />
              <span className="model-name-text">{model.name}</span>
            </div>
            <span className="model-provider-sub">{model.provider}</span>
          </div>
        );
      },
    },
    {
      key: 'masterModel',
      header: 'Master Model',
      sortValue: (r) => (r.override ? r.override.expertModel.name : routing.expertModel.name),
      render: (r) => {
        const model = r.override ? r.override.expertModel : routing.expertModel;
        return (
          <div className="model-cell">
            <div className="model-title-wrap">
              <TierBadge tier="EXPERT" />
              <span className="model-name-text">{model.name}</span>
              {r.override && <span className="override-chip"><Pencil size={11} /> Override</span>}
            </div>
            <span className="model-provider-sub">{model.provider}</span>
          </div>
        );
      },
    },
    { key: 'cost', header: 'Cost', align: 'right', sortValue: (r) => r.cost, render: (r) => <span className="tnum">{formatUsd(r.cost)}</span> },
    { key: 'savings', header: 'Est. Savings', align: 'right', sortValue: (r) => r.savings, render: (r) => <span className="tnum delta-good">+{formatUsd(r.savings)}</span> },
    { key: 'requests', header: 'Requests', align: 'right', sortValue: (r) => r.requests, render: (r) => <span className="tnum">{formatInt(r.requests)}</span> },
    {
      key: 'stories',
      header: 'Jira Stories',
      align: 'right',
      sortValue: (r) => r.storiesDone,
      render: (r) => {
        const pct = r.storiesAssigned > 0 ? Math.round((r.storiesDone / r.storiesAssigned) * 100) : 0;
        return (
          <div className="jira-cell">
            <div className="jira-numbers">
              <span className="tnum cell-strong">{r.storiesDone}/{r.storiesAssigned}</span>
              <span className="jira-pct">{pct}%</span>
            </div>
            <div className="progress-mini">
              <div className={`progress-mini-fill ${pct >= 75 ? 'good' : ''}`} style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
          </div>
        );
      },
    },
    {
      key: 'costPerStorySaved',
      header: 'Cost/story saved',
      align: 'right',
      sortValue: (r) => (r.storiesDone > 0 ? r.savings / r.storiesDone : -1),
      render: (r) => {
        const savedPerStory = r.storiesDone > 0 ? r.savings / r.storiesDone : null;
        return (
          <span className="tnum delta-good">
            {savedPerStory != null ? `+${formatUsd(savedPerStory)}` : '—'}
          </span>
        );
      },
    },
  ];

  const budgetPct = project.budgetUsedPct;
  const budgetBarClass = project.budgetState === 'EXCEEDED' ? 'danger' : project.budgetState === 'WARNING' ? 'warning' : 'ok';

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <button className="back-link" onClick={() => navigate('/admin')}>
            <ArrowLeft size={14} /> Overview
          </button>
          <h1>{project.name}</h1>
          <p className="subtle">
            <span className="mono">{project.key}</span> · {project.jiraProjectKey ? `Jira ${project.jiraProjectKey}` : 'No Jira link'} · {project.managers.map((m) => m.displayName).join(', ')}
          </p>
        </div>
        <div className="head-actions">
          <Button icon={<Download size={15} />} onClick={() => {}}>Export CSV</Button>
          <Button variant="primary" icon={<Pencil size={15} />} onClick={() => setShowRouting(true)}>Model routing</Button>
        </div>
      </div>

      {project.budgetUsd != null && budgetPct != null && (
        <section className="card budget-card">
          <div className="budget-head">
            <span>Monthly budget</span>
            <span className="tnum">{formatUsd(project.budgetUsedUsd)} of {formatUsd(project.budgetUsd)} · {budgetPct.toFixed(0)}%</span>
          </div>
          <div className="budget-bar">
            <div className={`budget-fill budget-${budgetBarClass}`} style={{ width: `${Math.min(100, budgetPct)}%` }} />
          </div>
          {project.budgetState === 'EXCEEDED' && <div className="budget-note danger">Budget exceeded this month.</div>}
          {project.budgetState === 'WARNING' && <div className="budget-note warning">Approaching budget threshold ({project.alertPct}%).</div>}
        </section>
      )}

      <div className="kpi-grid">
        <KpiTile label="Total tokens" value={formatTokens(c.totalTokens)} delta={{ current: c.totalTokens, previous: p.totalTokens }} icon={<Layers size={16} />} help="Total worker and expert tokens used within this project." />
        <KpiTile label="Cost" value={formatUsd(c.totalCost)} delta={{ current: c.totalCost, previous: p.totalCost, goodWhen: 'down' }} icon={<Coins size={16} />} help="Total actual cost billed by expert models for this project." />
        <KpiTile label="Est. savings" value={formatUsd(c.savings)} accent delta={{ current: c.savings, previous: p.savings }} icon={<TrendingUp size={16} />} help="Baseline (paid-only) cost minus actual cost." />
        <KpiTile label="Requests" value={formatInt(c.requests)} delta={{ current: c.requests, previous: p.requests }} help="Total IDE requests routed for this project." />
        <KpiTile label="Developers" value={formatInt(c.activeDevelopers)} icon={<Users size={16} />} help="Active developers contributing to this project." />
        <KpiTile label="Stories" value={`${c.storiesDone}/${c.storiesAssigned}`} delta={{ current: c.storiesDone, previous: p.storiesDone }} icon={<CheckCircle2 size={16} />} help="Jira stories assigned and completed in this project." />
      </div>

      <div className="routing-bar">
        <div className="routing-model">
          <TierBadge tier="WORKER" />
          <span className="routing-name">{routing.workerModel.name}</span>
        </div>
        <span className="routing-arrow">→</span>
        <div className="routing-model">
          <TierBadge tier="EXPERT" />
          <span className="routing-name">{routing.expertModel.name}</span>
        </div>
        <span className="routing-source subtle">override: {routing.source.toLowerCase()}</span>
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-head"><h2>Daily tokens</h2></div>
          <TokensStackedArea data={daily} />
        </section>
        <section className="card">
          <div className="card-head"><h2>Daily cost</h2></div>
          <CostLineChart data={daily} />
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Developers</h2>
          <span className="subtle">Click a row for details.</span>
        </div>
        <DataTable
          columns={cols}
          rows={developers}
          rowKey={(r) => r.userId}
          onRowClick={(r) => navigate(`/projects/${projectId}/members/${r.userId}`)}
          searchable
          searchKeys={(r) => r.displayName}
        />
      </section>

      <section className="card">
        <div className="card-head"><h2>Cost saved per story</h2></div>
        <CostPerStoryBar
          data={developers
            .filter((d) => d.storiesDone > 0)
            .map((d) => ({
              name: d.displayName.split(' ')[0],
              costPerStory: Math.round((d.savings / d.storiesDone) * 100) / 100,
            }))
            .slice(0, 10)}
          nameKey="name"
          valueKey="costPerStory"
        />
      </section>

      <RoutingModal
        open={showRouting}
        onClose={() => setShowRouting(false)}
        workerModels={workerModels}
        expertModels={expertModels}
        currentWorker={routing.workerModel}
        currentExpert={routing.expertModel}
      />
    </div>
  );
}

function RoutingModal({
  open,
  onClose,
  workerModels,
  expertModels,
  currentWorker,
  currentExpert,
}: {
  open: boolean;
  onClose: () => void;
  workerModels: ModelRef[];
  expertModels: ModelRef[];
  currentWorker: ModelRef;
  currentExpert: ModelRef;
}) {
  const [worker, setWorker] = useState(currentWorker.id);
  const [expert, setExpert] = useState(currentExpert.id);

  return (
    <Modal
      open={open}
      title="Model routing"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={onClose}>Save routing</Button>
        </>
      }
    >
      <p className="subtle" style={{ marginBottom: 16 }}>
        Choose the free worker model that prepares context, and the paid expert model that produces the final answer.
      </p>
      <Select label="Worker model (free)" value={worker} onChange={(e) => setWorker(Number(e.target.value))}>
        {workerModels.map((m) => (
          <option key={m.id} value={m.id}>{m.name}</option>
        ))}
      </Select>
      <Select label="Expert model (paid)" value={expert} onChange={(e) => setExpert(Number(e.target.value))}>
        {expertModels.map((m) => (
          <option key={m.id} value={m.id}>{m.name}</option>
        ))}
      </Select>
      <div className="modal-note subtle">
        Changes apply to the whole project and are recorded in the audit log. Developers will pick them up on their next request.
      </div>
    </Modal>
  );
}