import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import type { DailyPoint, ModelUsage } from '../api/types';
import { formatTokens, formatFullTokens, formatUsd, formatDate } from '../lib/format';

function chartTheme() {
  const s = getComputedStyle(document.documentElement);
  return {
    grid: s.getPropertyValue('--grid').trim() || '#e1e0d9',
    axis: s.getPropertyValue('--axis').trim() || '#c3c2b7',
    ink: s.getPropertyValue('--ink-2').trim() || '#52514e',
    series1: s.getPropertyValue('--series-1').trim() || '#2a78d6',
    series2: s.getPropertyValue('--series-2').trim() || '#eb6834',
    series3: s.getPropertyValue('--series-3').trim() || '#1baf7a',
  };
}

export function TokensStackedArea({ data }: { data: DailyPoint[] }) {
  const t = chartTheme();
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="gradWorker" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={t.series1} stopOpacity={0.4} />
            <stop offset="100%" stopColor={t.series1} stopOpacity={0.05} />
          </linearGradient>
          <linearGradient id="gradExpert" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={t.series2} stopOpacity={0.4} />
            <stop offset="100%" stopColor={t.series2} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey="day" tickFormatter={formatDate} stroke={t.axis} tickLine={false} fontSize={11} minTickGap={28} />
        <YAxis stroke={t.axis} tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => formatTokens(v)} width={52} />
        <RTooltip
          formatter={(value, name) => [formatFullTokens(Number(value)), String(name)]}
          labelFormatter={(label) => 'Day: ' + formatDate(String(label))}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: 'var(--ink)', fontWeight: 600 }}
        />
        <Legend formatter={(v) => (v === 'workerTokens' ? 'Worker (free)' : 'Expert (paid)')} wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="workerTokens" stackId="1" stroke={t.series1} fill="url(#gradWorker)" strokeWidth={2} />
        <Area type="monotone" dataKey="expertTokens" stackId="1" stroke={t.series2} fill="url(#gradExpert)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function CostByModelBar({ data }: { data: ModelUsage[] }) {
  const t = chartTheme();
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey="model" stroke={t.axis} tickLine={false} fontSize={11} interval={0} tickFormatter={(v) => (String(v).length > 12 ? String(v).slice(0, 12) + '…' : String(v))} />
        <YAxis stroke={t.axis} tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => formatUsd(v)} width={56} />
        <RTooltip
          formatter={(value) => [formatUsd(Number(value)), 'Cost']}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: 'var(--ink)', fontWeight: 600 }}
        />
        <Bar dataKey="cost" radius={[4, 4, 0, 0]} fill={t.series3} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CostLineChart({ data }: { data: DailyPoint[] }) {
  const t = chartTheme();
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="gradCost" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={t.series3} stopOpacity={0.4} />
            <stop offset="100%" stopColor={t.series3} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey="day" tickFormatter={formatDate} stroke={t.axis} tickLine={false} fontSize={11} minTickGap={28} />
        <YAxis stroke={t.axis} tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => formatUsd(v)} width={56} />
        <RTooltip
          formatter={(value, name) => [formatUsd(Number(value)), name === 'cost' ? 'Actual cost' : name === 'baselineCost' ? 'Baseline cost' : 'Savings']}
          labelFormatter={(label) => 'Day: ' + formatDate(String(label))}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: 'var(--ink)', fontWeight: 600 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="baselineCost" stroke={t.axis} strokeDasharray="4 3" fill="none" strokeWidth={1.5} />
        <Area type="monotone" dataKey="cost" stroke={t.series3} fill="url(#gradCost)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function CostPerStoryBar({ data, nameKey, valueKey }: { data: Record<string, unknown>[]; nameKey: string; valueKey: string }) {
  const t = chartTheme();
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey={nameKey} stroke={t.axis} tickLine={false} fontSize={11} interval={0} />
        <YAxis stroke={t.axis} tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v) => formatUsd(v)} width={56} />
        <RTooltip
          formatter={(value) => [formatUsd(Number(value)), 'Cost / story']}
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: 'var(--ink)', fontWeight: 600 }}
        />
        <Bar dataKey={valueKey} radius={[4, 4, 0, 0]} fill={t.series1} />
      </BarChart>
    </ResponsiveContainer>
  );
}