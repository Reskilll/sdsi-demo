import type { ReactNode } from 'react';
import clsx from 'clsx';
import { formatDelta } from '../lib/format';
import { Tooltip } from './Tooltip';

interface DeltaSpec {
  current: number;
  previous: number;
  // Overrides the default "up = good" heuristic:
  goodWhen?: 'up' | 'down';
  // Show a custom sign/label transform (true = show +/- % change):
  invertColor?: boolean;
}

interface Props {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  delta?: DeltaSpec;
  help?: ReactNode;
  accent?: boolean;
}

export function KpiTile({ label, value, icon, delta, help, accent }: Props) {
  let deltaNode: ReactNode = null;
  if (delta) {
    const d = formatDelta(delta.current, delta.previous);
    if (d.direction !== 'flat') {
      const good = delta.goodWhen === 'down' ? d.direction === 'down' : d.direction === 'up';
      const cls = delta.invertColor ? (good ? 'delta-good' : 'delta-bad') : d.direction === 'up' ? 'delta-up' : 'delta-down';
      deltaNode = <span className={clsx('delta-pill', cls)}>{d.value >= 0 ? '▲' : '▼'} {d.label}</span>;
    }
  }

  return (
    <div className={clsx('kpi', accent && 'kpi-accent')}>
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        {help && (
          <Tooltip label={help}>
            <span className="kpi-help" aria-label="info">
              ?
            </span>
          </Tooltip>
        )}
      </div>
      <div className="kpi-value tnum">{value}</div>
      <div className="kpi-bottom">
        {deltaNode}
        {icon && <span className="kpi-icon">{icon}</span>}
      </div>
    </div>
  );
}