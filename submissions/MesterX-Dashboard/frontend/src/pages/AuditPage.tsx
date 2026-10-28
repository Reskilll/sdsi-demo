import { useAudit } from '../api/hooks';
import { DataTable, type Column } from '../components/DataTable';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { formatDateTime } from '../lib/format';
import type { AuditEntry } from '../api/types';

function Diff({ before, after }: { before: unknown; after: unknown }) {
  return (
    <div className="audit-diff">
      {before != null && <div className="audit-line"><span className="audit-minus">−</span><code>{JSON.stringify(before)}</code></div>}
      {after != null && <div className="audit-line"><span className="audit-plus">+</span><code>{JSON.stringify(after)}</code></div>}
    </div>
  );
}

export function AuditPage() {
  const { data, isLoading, isError, error, refetch } = useAudit();

  const cols: Column<AuditEntry>[] = [
    { key: 'timestamp', header: 'Time', sortValue: (r) => r.timestamp, render: (r) => <span className="tnum subtle">{formatDateTime(r.timestamp)}</span> },
    { key: 'actor', header: 'Actor', sortValue: (r) => r.actor, render: (r) => <span className="cell-strong">{r.actor}</span> },
    { key: 'action', header: 'Action', sortValue: (r) => r.action, render: (r) => <span className="mono">{r.action}</span> },
    { key: 'entity', header: 'Entity', render: (r) => <span>{r.entity}{r.entityId ? ` #${r.entityId}` : ''}</span> },
    { key: 'change', header: 'Change', render: (r) => <Diff before={r.before} after={r.after} /> },
  ];

  if (isLoading) return <div className="page"><SkeletonBlock rows={5} /></div>;
  if (isError || !data) return <div className="page"><ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={refetch} /></div>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Audit log</h1>
          <p className="subtle">Every configuration change, recorded for accountability.</p>
        </div>
      </div>
      <section className="card">
        <DataTable columns={cols} rows={data} rowKey={(r) => r.id} />
      </section>
    </div>
  );
}