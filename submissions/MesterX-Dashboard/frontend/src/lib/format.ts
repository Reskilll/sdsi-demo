export function formatTokens(n: number): string {
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(2) + 'B';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  return String(Math.round(n));
}

export function formatFullTokens(n: number): string {
  return n.toLocaleString('en-US');
}

export function formatUsd(n: number, opts?: { sign?: boolean; decimals?: number }): string {
  const decimals = opts?.decimals ?? 2;
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000 && decimals <= 2) {
    const v = (n / 1_000_000_000).toFixed(2);
    return `${opts?.sign && n < 0 ? '-' : ''}$${Math.abs(parseFloat(v)).toFixed(2)}B`;
  }
  if (abs >= 1_000_000 && decimals <= 2) {
    const v = (n / 1_000_000).toFixed(2);
    return `${opts?.sign && n < 0 ? '-' : ''}$${Math.abs(parseFloat(v)).toFixed(2)}M`;
  }
  if (abs >= 1000 && decimals <= 2) {
    const v = (n / 1000).toFixed(1);
    return `${opts?.sign && n < 0 ? '-' : ''}$${Math.abs(parseFloat(v)).toFixed(1)}k`;
  }
  return `${n < 0 ? '-' : ''}$${Math.abs(n).toFixed(decimals)}`;
}

export function formatUsdExact(n: number): string {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

export function formatPct(n: number, decimals = 1): string {
  return n.toFixed(decimals) + '%';
}

export function formatInt(n: number): string {
  return n.toLocaleString('en-US');
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatMs(ms: number): string {
  if (ms >= 1000) return (ms / 1000).toFixed(1) + 's';
  return Math.round(ms) + 'ms';
}

export function formatDelta(cur: number, prev: number): { value: number; direction: 'up' | 'down' | 'flat'; good: boolean; label: string } {
  const value = prev === 0 ? 0 : ((cur - prev) / prev) * 100;
  const direction = value > 0.05 ? 'up' : value < -0.05 ? 'down' : 'flat';
  return { value, direction, good: true, label: `${value >= 0 ? '+' : ''}${value.toFixed(1)}%` };
}