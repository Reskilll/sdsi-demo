import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderKanban, Users, TrendingUp, CheckCircle2, ExternalLink } from 'lucide-react';
import { useAdminProjects, useProjectMembers } from '../api/hooks';
import { DataTable, type Column } from '../components/DataTable';
import { KpiTile } from '../components/KpiTile';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { TierBadge, Badge } from '../components/Badge';
import { formatUsd, formatInt } from '../lib/format';
import type { AdminProject, ProjectMemberRow } from '../api/types';

export function AdminProjectsPage() {
  const navigate = useNavigate();
  const [selectedProjectId, setSelectedProjectId] = useState<number | 'ALL'>('ALL');
  const [activeTab, setActiveTab] = useState<'members' | 'budgets'>('members');

  const {
    data: projects,
    isLoading: isProjectsLoading,
    isError: isProjectsError,
    error: projectsError,
    refetch: refetchProjects,
  } = useAdminProjects();

  const {
    data: allMembers,
    isLoading: isMembersLoading,
    isError: isMembersError,
    error: membersError,
    refetch: refetchMembers,
  } = useProjectMembers();

  // Filter members based on selected project
  const filteredMembers = useMemo(() => {
    if (!allMembers) return [];
    if (selectedProjectId === 'ALL') return allMembers;
    return allMembers.filter((m) => m.projectId === selectedProjectId);
  }, [allMembers, selectedProjectId]);

  // Aggregate high level KPIs
  const summaryKpis = useMemo(() => {
    if (!filteredMembers.length) {
      return { totalSavings: 0, totalCost: 0, storiesDone: 0, storiesAssigned: 0 };
    }
    const totalSavings = filteredMembers.reduce((acc, m) => acc + m.savings, 0);
    const totalCost = filteredMembers.reduce((acc, m) => acc + m.cost, 0);
    const storiesDone = filteredMembers.reduce((acc, m) => acc + m.storiesDone, 0);
    const storiesAssigned = filteredMembers.reduce((acc, m) => acc + m.storiesAssigned, 0);
    return { totalSavings, totalCost, storiesDone, storiesAssigned };
  }, [filteredMembers]);

  // Columns for the Project-Wise Member & Model Routing table
  const memberCols: Column<ProjectMemberRow>[] = [
    {
      key: 'project',
      header: 'Project',
      sortValue: (r) => r.projectName,
      render: (r) => (
        <div className="project-tag">
          <span className="project-name-strong">{r.projectName}</span>
          <span className="project-badge-pill">{r.projectKey}</span>
        </div>
      ),
    },
    {
      key: 'member',
      header: 'Member',
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
      sortValue: (r) => r.workerModel.name,
      render: (r) => (
        <div className="model-cell">
          <div className="model-title-wrap">
            <TierBadge tier="WORKER" />
            <span className="model-name-text">{r.workerModel.name}</span>
          </div>
          <span className="model-provider-sub">{r.workerModel.provider}</span>
        </div>
      ),
    },
    {
      key: 'masterModel',
      header: 'Master Model',
      sortValue: (r) => r.expertModel.name,
      render: (r) => (
        <div className="model-cell">
          <div className="model-title-wrap">
            <TierBadge tier="EXPERT" />
            <span className="model-name-text">{r.expertModel.name}</span>
            {r.isOverride && <Badge tone="warning">Override</Badge>}
          </div>
          <span className="model-provider-sub">{r.expertModel.provider}</span>
        </div>
      ),
    },
    {
      key: 'savings',
      header: 'Cost & Savings',
      align: 'right',
      sortValue: (r) => r.savings,
      render: (r) => (
        <div className="savings-cell">
          <span className="savings-val">+{formatUsd(r.savings)} saved</span>
          <span className="cost-sub">Cost: {formatUsd(r.cost)} · {Math.round((r.cost / 50) * 100)}% of $50 cap</span>
        </div>
      ),
    },
    {
      key: 'costPerStorySaved',
      header: 'Cost/story saved',
      align: 'right',
      sortValue: (r) => (r.storiesDone > 0 ? r.savings / r.storiesDone : -1),
      render: (r) => {
        const saved = r.storiesDone > 0 ? r.savings / r.storiesDone : null;
        return (
          <span className="tnum delta-good">
            {saved != null ? `+${formatUsd(saved)}` : '—'}
          </span>
        );
      },
    },
    {
      key: 'jiraStatus',
      header: 'Jira Stories',
      align: 'right',
      sortValue: (r) => r.storiesDone,
      render: (r) => {
        const pct = r.storiesAssigned > 0 ? Math.round((r.storiesDone / r.storiesAssigned) * 100) : 0;
        return (
          <div className="jira-cell">
            <div className="jira-numbers">
              <span className="tnum cell-strong">
                {r.storiesDone}/{r.storiesAssigned}
              </span>
              <span className="jira-pct">{pct}% Done</span>
            </div>
            <div className="progress-mini">
              <div
                className={`progress-mini-fill ${pct >= 75 ? 'good' : ''}`}
                style={{ width: `${Math.min(100, pct)}%` }}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (r) => (
        <button
          className="icon-btn"
          title="View developer details"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/projects/${r.projectId}/members/${r.userId}`);
          }}
        >
          <ExternalLink size={14} />
        </button>
      ),
    },
  ];

  // Columns for the Project Budgets administrative table
  const budgetCols: Column<AdminProject>[] = [
    { key: 'key', header: 'Key', sortValue: (r) => r.key, render: (r) => <span className="mono">{r.key}</span> },
    { key: 'name', header: 'Project', sortValue: (r) => r.name, render: (r) => <span className="cell-strong">{r.name}</span> },
    {
      key: 'jiraProjectKey',
      header: 'Jira key',
      render: (r) => (r.jiraProjectKey ? <span className="mono">{r.jiraProjectKey}</span> : <span className="subtle">—</span>),
    },
    {
      key: 'memberCount',
      header: 'Members',
      align: 'right',
      sortValue: (r) => r.memberCount,
      render: (r) => <span className="tnum">{formatInt(r.memberCount)}</span>,
    },
    { key: 'managers', header: 'Managers', render: (r) => <span>{r.managers.join(', ')}</span> },
    {
      key: 'budgetUsd',
      header: 'Budget',
      align: 'right',
      sortValue: (r) => r.budgetUsd ?? -1,
      render: (r) => <span className="tnum">{r.budgetUsd != null ? formatUsd(r.budgetUsd) : '—'}</span>,
    },
    { key: 'alertPct', header: 'Alert at', align: 'right', render: (r) => <span className="tnum">{r.alertPct}%</span> },
    {
      key: 'open',
      header: '',
      align: 'right',
      render: (r) => (
        <button
          className="icon-btn"
          title="Open project dashboard"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/projects/${r.id}`);
          }}
        >
          <ExternalLink size={14} />
        </button>
      ),
    },
  ];

  if (isProjectsLoading || isMembersLoading) {
    return (
      <div className="page">
        <SkeletonBlock rows={6} />
      </div>
    );
  }

  if (isProjectsError || isMembersError || !projects || !allMembers) {
    return (
      <div className="page">
        <ErrorBanner
          message={(projectsError || membersError) instanceof Error ? (projectsError || membersError)!.message : 'Failed to load projects'}
          onRetry={() => {
            refetchProjects();
            refetchMembers();
          }}
        />
      </div>
    );
  }

  const completionPct =
    summaryKpis.storiesAssigned > 0 ? Math.round((summaryKpis.storiesDone / summaryKpis.storiesAssigned) * 100) : 0;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Projects & Model Routing</h1>
          <p className="subtle">Project-wise developer allocation, worker & master models, cost savings, and Jira status.</p>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiTile
          label="Active Projects"
          value={formatInt(projects.length)}
          icon={<FolderKanban size={16} />}
          help="Active projects being tracked and routed in the organisation."
        />
        <KpiTile
          label="Member Allocations"
          value={formatInt(filteredMembers.length)}
          icon={<Users size={16} />}
          help="Total developer assignments across the selected project scope."
        />
        <KpiTile
          label="Est. Cost Savings"
          value={formatUsd(summaryKpis.totalSavings)}
          accent
          icon={<TrendingUp size={16} />}
          help="Net savings achieved by routing queries through the free worker tier before the expert master model."
        />
        <KpiTile
          label="Jira Delivery"
          value={`${summaryKpis.storiesDone}/${summaryKpis.storiesAssigned}`}
          icon={<CheckCircle2 size={16} />}
          help={`${completionPct}% of assigned Jira stories moved to Done.`}
        />
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label className="field-label" style={{ marginBottom: 0 }}>
            Filter by Project:
          </label>
          <select
            className="select"
            style={{ width: 'auto', minWidth: 200 }}
            value={selectedProjectId}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedProjectId(val === 'ALL' ? 'ALL' : Number(val));
            }}
          >
            <option value="ALL">Organisation-level</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.key})
              </option>
            ))}
          </select>
        </div>

        <div className="view-tabs">
          <button
            className={`view-tab ${activeTab === 'members' ? 'active' : ''}`}
            onClick={() => setActiveTab('members')}
          >
            Project Members & Models
          </button>
          <button
            className={`view-tab ${activeTab === 'budgets' ? 'active' : ''}`}
            onClick={() => setActiveTab('budgets')}
          >
            Project Budgets & Limits
          </button>
        </div>
      </div>

      <section className="card">
        {activeTab === 'members' ? (
          <>
            <div className="card-head">
              <h2>Project-Wise Members & Model Allocation</h2>
              <span className="subtle">Click any member to inspect usage telemetry and prompt events.</span>
            </div>
            <DataTable
              columns={memberCols}
              rows={filteredMembers}
              rowKey={(r) => `${r.projectId}-${r.userId}`}
              onRowClick={(r) => navigate(`/projects/${r.projectId}/members/${r.userId}`)}
              searchable
              searchPlaceholder="Search project, member, or model…"
              searchKeys={(r) => `${r.projectName} ${r.projectKey} ${r.displayName} ${r.workerModel.name} ${r.expertModel.name}`}
            />
          </>
        ) : (
          <>
            <div className="card-head">
              <h2>Project Configurations & Budgets</h2>
              <span className="subtle">Overview of project keys, managers, and monthly thresholds.</span>
            </div>
            <DataTable
              columns={budgetCols}
              rows={projects}
              rowKey={(r) => r.id}
              onRowClick={(r) => navigate(`/projects/${r.id}`)}
              searchable
              searchPlaceholder="Search project name or key…"
              searchKeys={(r) => `${r.name} ${r.key}`}
            />
          </>
        )}
      </section>
    </div>
  );
}
