import type { DayOfWeek, Room } from '../api/types';
import { WEEKDAY_LABELS, WEEKDAY_ORDER, formatTime } from './time';

const AMENITY_LABELS: Record<string, string> = {
  tv: 'TV',
  video: 'Video call',
  whiteboard: 'Whiteboard',
  projector: 'Projector',
  speakerphone: 'Speakerphone',
  accessibility: 'Accessible',
};

export function amenityLabel(amenity: string): string {
  const known = AMENITY_LABELS[amenity.toLowerCase()];
  if (known) return known;
  return amenity
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function roomLocation(room: Room): string {
  const pieces: string[] = [];
  if (typeof room.floor === 'number') pieces.push(`Floor ${room.floor}`);
  if (room.location) pieces.push(room.location);
  return pieces.join(' \u00b7 ');
}

export function roomCapacityLabel(room: Room): string {
  return `${room.capacity} ${room.capacity === 1 ? 'seat' : 'seats'}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  return parts
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

/** Splits comma/newline/semicolon input, trims, and removes case-insensitive duplicates. */
export function parseAttendeeNames(raw: string): string[] {
  const seen = new Set<string>();
  const names: string[] = [];
  for (const piece of raw.split(/[,\n;]+/)) {
    const name = piece.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    names.push(name);
  }
  return names;
}

export function sortedWeekdays(days: DayOfWeek[]): DayOfWeek[] {
  return [...days].sort(
    (left, right) => WEEKDAY_ORDER.indexOf(left) - WEEKDAY_ORDER.indexOf(right),
  );
}

export function weekdaySummary(days: DayOfWeek[]): string {
  if (days.length === 0) return 'Start-date weekday';
  if (days.length === 7) return 'Every day';
  return sortedWeekdays(days)
    .map((day) => WEEKDAY_LABELS[day].short)
    .join(', ');
}

export function scheduleSummary(days: DayOfWeek[], startTime: string, endTime: string): string {
  return `${weekdaySummary(days)} \u00b7 ${formatTime(startTime)}\u2013${formatTime(endTime)}`;
}

export function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'booking';
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural ?? `${singular}s`);
}
