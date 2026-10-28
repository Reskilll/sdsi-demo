import { useAdminUsers } from '../api/hooks';
import { DataTable, type Column } from '../components/DataTable';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { RoleBadge } from '../components/Badge';
import { formatDateTime } from '../lib/format';
import type { AdminUser } from '../api/types';

export function UsersPage() {
  const { data, isLoading, isError, error, refetch } = useAdminUsers();

  const cols: Column<AdminUser>[] = [
    { key: 'displayName', header: 'User', sortValue: (r) => r.displayName, render: (r) => <span className="cell-strong">{r.displayName}</span> },
    { key: 'email', header: 'Email', sortValue: (r) => r.email, render: (r) => <span className="subtle">{r.email}</span> },
    { key: 'role', header: 'Role', sortValue: (r) => r.role, render: (r) => <RoleBadge role={r.role} /> },
    { key: 'projects', header: 'Projects', sortValue: (r) => r.projects.length, align: 'right', render: (r) => <span className="tnum">{r.projects.length}</span> },
    { key: 'lastSeen', header: 'Last seen', align: 'right', sortValue: (r) => r.lastSeen ?? '', render: (r) => <span className="tnum subtle">{r.lastSeen ? formatDateTime(r.lastSeen) : '—'}</span> },
    { key: 'keys', header: 'API keys', align: 'right', sortValue: (r) => r.apiKeys.filter((k) => !k.revokedAt).length, render: (r) => <span className="tnum">{r.apiKeys.filter((k) => !k.revokedAt).length} active</span> },
  ];

  if (isLoading) return <div className="page"><SkeletonBlock rows={5} /></div>;
  if (isError || !data) return <div className="page"><ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={refetch} /></div>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Users</h1>
          <p className="subtle">Developers, project managers, and their plugin API keys.</p>
        </div>
      </div>
      <section className="card">
        <DataTable columns={cols} rows={data} rowKey={(r) => r.id} searchable searchKeys={(r) => r.displayName + r.email} />
      </section>
    </div>
  );
}