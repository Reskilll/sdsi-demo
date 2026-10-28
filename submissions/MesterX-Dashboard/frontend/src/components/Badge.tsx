import clsx from 'clsx';

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const TONES: Record<Tone, string> = {
  neutral: 'badge-neutral',
  accent: 'badge-accent',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge-info',
};

export function Badge({ tone = 'neutral', children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return <span className={clsx('badge', TONES[tone], className)}>{children}</span>;
}

export function TierBadge({ tier }: { tier: 'WORKER' | 'EXPERT' }) {
  return <Badge tone={tier === 'WORKER' ? 'info' : 'accent'}>{tier === 'WORKER' ? 'Worker' : 'Expert'}</Badge>;
}

export function RoleBadge({ role }: { role: string }) {
  const tone: Tone = role === 'ADMIN' ? 'danger' : role === 'PROJECT_MANAGER' ? 'warning' : 'neutral';
  const label = role === 'PROJECT_MANAGER' ? 'PM' : role.charAt(0) + role.slice(1).toLowerCase().replace('_', ' ');
  return <Badge tone={tone}>{label}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, Tone> = {
    ACTIVE: 'success',
    DISABLED: 'neutral',
    DONE: 'success',
    IN_PROGRESS: 'warning',
    TODO: 'neutral',
    SUCCESS: 'success',
    ERROR: 'danger',
    WORKER_ONLY: 'info',
    OK: 'success',
    WARNING: 'warning',
    EXCEEDED: 'danger',
  };
  const tone = map[status] ?? 'neutral';
  return <Badge tone={tone}>{status.replace(/_/g, ' ')}</Badge>;
}