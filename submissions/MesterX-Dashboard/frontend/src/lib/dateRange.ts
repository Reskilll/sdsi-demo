export interface DateRange {
  from: string; // ISO yyyy-mm-dd
  to: string;
}

export type PresetKey = '7d' | '30d' | '90d' | 'month';

const MS_DAY = 86400000;

export function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function rangeFor(preset: PresetKey | 'custom', custom?: DateRange): DateRange {
  const now = new Date();
  const to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  switch (preset) {
    case '7d':
      return { from: iso(new Date(to.getTime() - 6 * MS_DAY)), to: iso(to) };
    case '30d':
      return { from: iso(new Date(to.getTime() - 29 * MS_DAY)), to: iso(to) };
    case '90d':
      return { from: iso(new Date(to.getTime() - 89 * MS_DAY)), to: iso(to) };
    case 'month': {
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return { from: iso(start), to: iso(to) };
    }
    case 'custom':
      return custom ?? rangeFor('30d');
  }
}

export function defaultRange(): DateRange {
  return rangeFor('30d');
}