import type { DayOfWeek } from '../api/types';

/**
 * Wall-clock helpers.
 *
 * The API deliberately sends local date-times without offsets. We never feed
 * them to `new Date(value)`, because that would reinterpret the value in the
 * browser's timezone. Instead we parse the string parts and format manually,
 * so 10:00 stays 10:00 everywhere. Date arithmetic uses UTC *only* as a
 * calendar calculator, never for display conversion.
 */

export const OPEN_MINUTES = 9 * 60;
export const CLOSE_MINUTES = 18 * 60;
export const MIN_DURATION_MINUTES = 15;
export const DAY_MINUTES = 24 * 60;

const MONTHS_SHORT = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const;

const MONTHS_LONG = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;

const WEEKDAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;
const WEEKDAYS_LONG = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const;

const WEEKDAY_BY_INDEX: readonly DayOfWeek[] = [
  'SUNDAY',
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
];

export const WEEKDAY_ORDER: readonly DayOfWeek[] = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY',
];

export const WEEKDAY_LABELS: Record<DayOfWeek, { short: string; long: string }> = {
  MONDAY: { short: 'Mon', long: 'Monday' },
  TUESDAY: { short: 'Tue', long: 'Tuesday' },
  WEDNESDAY: { short: 'Wed', long: 'Wednesday' },
  THURSDAY: { short: 'Thu', long: 'Thursday' },
  FRIDAY: { short: 'Fri', long: 'Friday' },
  SATURDAY: { short: 'Sat', long: 'Saturday' },
  SUNDAY: { short: 'Sun', long: 'Sunday' },
};

export interface DateParts {
  year: number;
  month: number;
  day: number;
}

export interface TimeParts {
  hour: number;
  minute: number;
  second: number;
}

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

export function parseDateParts(value: string): DateParts | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const check = new Date(Date.UTC(year, month - 1, day));
  if (
    check.getUTCFullYear() !== year ||
    check.getUTCMonth() !== month - 1 ||
    check.getUTCDate() !== day
  ) {
    return null;
  }
  return { year, month, day };
}

export function parseTimeParts(value: string): TimeParts | null {
  const match = /(?:^|T)(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = match[3] === undefined ? 0 : Number(match[3]);
  if (hour > 23 || minute > 59 || second > 59) return null;
  return { hour, minute, second };
}

export function dateOf(value: string): string {
  return value.slice(0, 10);
}

export function timeOf(value: string): string {
  const parts = parseTimeParts(value);
  return parts ? `${pad2(parts.hour)}:${pad2(parts.minute)}` : '';
}

export function formatTime(value: string): string {
  return timeOf(value) || value;
}

export function formatTimeRange(start: string, end: string): string {
  return `${formatTime(start)}\u2013${formatTime(end)}`;
}

function weekdayIndex(value: string): number {
  const parts = parseDateParts(value);
  if (!parts) return -1;
  return new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay();
}

export function weekdayOf(value: string): DayOfWeek | null {
  const index = weekdayIndex(value);
  return index < 0 ? null : WEEKDAY_BY_INDEX[index] ?? null;
}

export function weekdayLabel(day: DayOfWeek, style: 'short' | 'long' = 'short'): string {
  return style === 'short' ? WEEKDAY_LABELS[day].short : WEEKDAY_LABELS[day].long;
}

export type DateStyle = 'short' | 'long';

export function formatDate(value: string, style: DateStyle = 'short'): string {
  const parts = parseDateParts(value);
  const index = weekdayIndex(value);
  if (!parts || index < 0) return value;
  if (style === 'long') {
    return `${WEEKDAYS_LONG[index]} ${parts.day} ${MONTHS_LONG[parts.month - 1]} ${parts.year}`;
  }
  return `${WEEKDAYS_SHORT[index]} ${parts.day} ${MONTHS_SHORT[parts.month - 1]} ${parts.year}`;
}

export function formatDateTimeRange(start: string, end: string): string {
  return `${formatDate(start)} \u00b7 ${formatTimeRange(start, end)}`;
}

export function formatDuration(minutes: number): string {
  const safe = Math.max(0, Math.round(minutes));
  const hours = Math.floor(safe / 60);
  const rest = safe % 60;
  if (hours === 0) return `${rest} min`;
  if (rest === 0) return `${hours} h`;
  return `${hours} h ${rest} min`;
}

/** Minutes since midnight for a time or an ISO local date-time. */
export function minutesOfDay(value: string): number | null {
  const parts = parseTimeParts(value);
  return parts ? parts.hour * 60 + parts.minute : null;
}

/** Minutes since the office opened (09:00). Negative before opening. */
export function minutesFromOpen(value: string): number | null {
  const minutes = minutesOfDay(value);
  return minutes === null ? null : minutes - OPEN_MINUTES;
}

export function minutesToTime(minutes: number): string {
  const safe = ((Math.round(minutes) % DAY_MINUTES) + DAY_MINUTES) % DAY_MINUTES;
  return `${pad2(Math.floor(safe / 60))}:${pad2(safe % 60)}`;
}

export function addMinutesToTime(time: string, minutes: number): string {
  const parts = parseTimeParts(time);
  if (!parts) return time;
  return minutesToTime(parts.hour * 60 + parts.minute + minutes);
}

export function roundToStep(minutes: number, step = 15): number {
  if (step <= 0) return minutes;
  return Math.round(minutes / step) * step;
}

/**
 * Half-open interval overlap: 10:00–11:00 and 11:00–12:00 do not clash.
 * Inputs are canonical wall-clock ISO values, so lexical comparison is exact.
 */
export function overlaps(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
  return aStart < bEnd && bStart < aEnd;
}

export function combineDateTime(date: string, time: string): string {
  const parts = parseTimeParts(time);
  if (!parts) return `${date}T${time}`;
  return `${date}T${pad2(parts.hour)}:${pad2(parts.minute)}:${pad2(parts.second)}`;
}

export function durationMinutes(start: string, end: string): number {
  const startParts = parseTimeParts(start);
  const endParts = parseTimeParts(end);
  if (!startParts || !endParts) return 0;
  return endParts.hour * 60 + endParts.minute - (startParts.hour * 60 + startParts.minute);
}

/** Client-side mirror of the office-hours rule; returns a user-facing message. */
export function validateWindow(startTime: string, endTime: string): string | null {
  const start = parseTimeParts(startTime);
  const end = parseTimeParts(endTime);
  if (!start || !end) return 'Enter a valid start and end time.';
  const startMinutes = start.hour * 60 + start.minute;
  const endMinutes = end.hour * 60 + end.minute;
  if (endMinutes <= startMinutes) return 'The end time must be after the start time.';
  if (endMinutes - startMinutes < MIN_DURATION_MINUTES) {
    return `A booking must be at least ${MIN_DURATION_MINUTES} minutes long.`;
  }
  if (startMinutes < OPEN_MINUTES || endMinutes > CLOSE_MINUTES) {
    return 'Bookings must fit between 09:00 and 18:00.';
  }
  return null;
}

export function addDays(value: string, days: number): string {
  const parts = parseDateParts(value);
  if (!parts) return value;
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + days));
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

/** Local calendar date as YYYY-MM-DD (the browser's office-local date). */
export function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
}

/** Local wall-clock now formatted for API filters, e.g. 2026-11-02T10:15:00. */
export function isoLocalNow(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}T${pad2(
    now.getHours(),
  )}:${pad2(now.getMinutes())}:${pad2(now.getSeconds())}`;
}

/** Sensible default start: the next quarter-hour today, otherwise 10:00. */
export function defaultStartTime(date: string): string {
  if (date !== todayISO()) return '10:00';
  const now = new Date();
  const next = Math.ceil((now.getHours() * 60 + now.getMinutes()) / 15) * 15;
  if (next < OPEN_MINUTES) return '09:00';
  if (next > CLOSE_MINUTES - 60) return '17:00';
  return minutesToTime(next);
}
