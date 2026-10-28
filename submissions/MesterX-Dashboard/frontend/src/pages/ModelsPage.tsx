import { useModels } from '../api/hooks';
import { DataTable, type Column } from '../components/DataTable';
import { SkeletonBlock } from '../components/Skeleton';
import { ErrorBanner } from '../components/StateViews';
import { TierBadge } from '../components/Badge';
import { formatUsd } from '../lib/format';
import type { Model } from '../api/types';

export function ModelsPage() {
  const { data, isLoading, isError, error, refetch } = useModels();

  const cols: Column<Model>[] = [
    { key: 'name', header: 'Model', sortValue: (r) => r.name, render: (r) => <span className="cell-strong">{r.name}</span> },
    { key: 'provider', header: 'Provider', sortValue: (r) => r.provider, render: (r) => <span>{r.provider}</span> },
    { key: 'tier', header: 'Tier', sortValue: (r) => r.tier, render: (r) => <TierBadge tier={r.tier} /> },
    { key: 'inputPer1k', header: 'In / 1K', align: 'right', sortValue: (r) => r.inputPer1k, render: (r) => <span className="tnum">{r.inputPer1k === 0 ? 'Free' : formatUsd(r.inputPer1k, { decimals: 2 })}</span> },
    { key: 'outputPer1k', header: 'Out / 1K', align: 'right', sortValue: (r) => r.outputPer1k, render: (r) => <span className="tnum">{r.outputPer1k === 0 ? 'Free' : formatUsd(r.outputPer1k, { decimals: 2 })}</span> },
    { key: 'enabled', header: 'Enabled', sortValue: (r) => (r.enabled ? 1 : 0), render: (r) => <span className={r.enabled ? 'dot dot-on' : 'dot'}>{r.enabled ? 'On' : 'Off'}</span> },
  ];

  if (isLoading) return <div className="page"><SkeletonBlock rows={5} /></div>;
  if (isError || !data) return <div className="page"><ErrorBanner message={error instanceof Error ? error.message : 'Failed to load'} onRetry={refetch} /></div>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Models</h1>
          <p className="subtle">The model catalogue and pricing used to compute cost.</p>
        </div>
      </div>
      <section className="card">
        <DataTable columns={cols} rows={data} rowKey={(r) => r.id} searchable searchKeys={(r) => r.name + r.provider} />
      </section>
      <p className="page-foot-note subtle">Worker models are free; expert models carry per-1K-token prices. Price changes keep history, so past costs are never rewritten.</p>
    </div>
  );
}