import { getEnv } from "@/lib/env";
import type { BusinessCalendarConfig } from "@/types";

/**
 * Business Calendar Service
 *
 * Determines which instants are "business hours" and provides
 * utilities for navigating the business calendar.
 *
 * Working days: Monday–Friday
 * Working hours: BUSINESS_START_HOUR to BUSINESS_END_HOUR in APP_TIMEZONE
 * Excludes: weekends and active holidays
 */

/** Lazy accessor — only resolved when defaults are needed */
let _cachedEnv: ReturnType<typeof getEnv> | null = null;
function env() {
  if (!_cachedEnv) _cachedEnv = getEnv();
  return _cachedEnv;
}

/**
 * Convert a Date to a timezone-aware date string "YYYY-MM-DD"
 * in the business timezone.
 */
export function toBusinessDateString(date: Date, timezone?: string): string {
  const tz = timezone || env().APP_TIMEZONE;
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(date);
}

/**
 * Get the hour (0-23) of a date in the business timezone.
 */
export function getBusinessHour(date: Date, timezone?: string): number {
  const tz = timezone || env().APP_TIMEZONE;
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour: "2-digit",
    hour12: false,
  });
  return parseInt(formatter.format(date), 10);
}

/**
 * Get the minute (0-59) of a date in the business timezone.
 */
export function getBusinessMinute(date: Date, timezone?: string): number {
  const tz = timezone || env().APP_TIMEZONE;
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    minute: "2-digit",
  });
  return parseInt(formatter.format(date), 10);
}

/**
 * Get the day of week (1=Monday, ..., 7=Sunday) in the business timezone.
 */
export function getBusinessDayOfWeek(date: Date, timezone?: string): number {
  const tz = timezone || env().APP_TIMEZONE;
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
  });
  const dayMap: Record<string, number> = {
    Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7,
  };
  return dayMap[formatter.format(date)] || 7;
}

/**
 * Check if a date falls on a weekend in the business timezone.
 */
export function isWeekend(date: Date, timezone?: string): boolean {
  const dow = getBusinessDayOfWeek(date, timezone);
  return dow >= 6;
}

/**
 * Check if a date falls on an active holiday.
 */
export function isHoliday(date: Date, holidays: Date[], timezone?: string): boolean {
  if (!holidays || holidays.length === 0) return false;
  const dateStr = toBusinessDateString(date, timezone);
  return holidays.some((h) => toBusinessDateString(h, timezone) === dateStr);
}

/**
 * Check if a date is within business hours (Mon–Fri, 9–18, non-holiday).
 */
export function isBusinessHour(
  date: Date,
  config?: BusinessCalendarConfig,
): boolean {
  const timezone = config?.timezone || env().APP_TIMEZONE;
  const startHour = config?.businessStartHour ?? env().BUSINESS_START_HOUR;
  const endHour = config?.businessEndHour ?? env().BUSINESS_END_HOUR;
  const holidays = config?.holidays || [];

  if (isWeekend(date, timezone)) return false;
  if (isHoliday(date, holidays, timezone)) return false;

  const hour = getBusinessHour(date, timezone);
  const minute = getBusinessMinute(date, timezone);
  const timeInMinutes = hour * 60 + minute;
  const startInMinutes = startHour * 60;
  const endInMinutes = endHour * 60;

  return timeInMinutes >= startInMinutes && timeInMinutes < endInMinutes;
}

/**
 * Get the start of the next business period after a given date.
 */
export function nextBusinessStart(
  date: Date,
  config?: BusinessCalendarConfig,
): Date {
  const timezone = config?.timezone || env().APP_TIMEZONE;
  const startHour = config?.businessStartHour ?? env().BUSINESS_START_HOUR;
  const holidays = config?.holidays || [];

  const dateStr = toBusinessDateString(date, timezone);
  const candidate = new Date(`${dateStr}T${String(startHour).padStart(2, "0")}:00:00`);

  if (date > candidate) {
    candidate.setDate(candidate.getDate() + 1);
  }

  for (let i = 0; i < 30; i++) {
    if (!isWeekend(candidate, timezone) && !isHoliday(candidate, holidays, timezone)) {
      break;
    }
    candidate.setDate(candidate.getDate() + 1);
  }

  return candidate;
}

/**
 * Get the end of the business day containing the given date.
 */
export function getBusinessEndOfDay(
  date: Date,
  config?: BusinessCalendarConfig,
): Date {
  const timezone = config?.timezone || env().APP_TIMEZONE;
  const endHour = config?.businessEndHour ?? env().BUSINESS_END_HOUR;
  const dateStr = toBusinessDateString(date, timezone);
  return new Date(`${dateStr}T${String(endHour).padStart(2, "0")}:00:00`);
}

/**
 * Calculate the total business minutes between two dates.
 * Excludes non-working hours, weekends, and holidays.
 */
export function calculateBusinessMinutes(
  startDate: Date,
  endDate: Date,
  config?: BusinessCalendarConfig,
): number {
  const timezone = config?.timezone || env().APP_TIMEZONE;
  const startHour = config?.businessStartHour ?? env().BUSINESS_START_HOUR;
  const endHour = config?.businessEndHour ?? env().BUSINESS_END_HOUR;
  const holidays = config?.holidays || [];

  if (endDate <= startDate) return 0;

  let totalMinutes = 0;
  const current = new Date(startDate);
  const end = new Date(endDate);

  // Fast path: if diff is large (>14 days), use day-based approximation
  const diffHours = (end.getTime() - startDate.getTime()) / 3600000;
  const useApproximation = diffHours > 336; // > 14 days

  if (useApproximation) {
    // Day-based approximation for very long intervals
    const businessMinutesPerDay = (endHour - startHour) * 60;
    const oneDay = 86400000;
    let cursor = new Date(startDate);
    while (cursor < end) {
      if (isBusinessHour(cursor, { timezone, businessStartHour: startHour, businessEndHour: endHour, holidays })) {
        totalMinutes++;
      }
      // Jump by 10 minutes at a time for performance
      cursor.setMinutes(cursor.getMinutes() + 10);
    }
    return totalMinutes;
  }

  // Precise minute-by-minute for typical durations
  current.setSeconds(0, 0);
  while (current < end) {
    if (isBusinessHour(current, { timezone, businessStartHour: startHour, businessEndHour: endHour, holidays })) {
      totalMinutes++;
    }
    current.setMinutes(current.getMinutes() + 1);
  }

  return totalMinutes;
}

/**
 * Add business minutes to a start date and return the resulting date.
 */
export function addBusinessMinutes(
  startDate: Date,
  minutes: number,
  config?: BusinessCalendarConfig,
): Date {
  const timezone = config?.timezone || env().APP_TIMEZONE;
  const startHour = config?.businessStartHour ?? env().BUSINESS_START_HOUR;
  const endHour = config?.businessEndHour ?? env().BUSINESS_END_HOUR;
  const holidays = config?.holidays || [];

  if (minutes <= 0) {
    return nextBusinessStart(startDate, config);
  }

  let current = nextBusinessStart(startDate, config);
  let remaining = minutes;

  const maxIterations = minutes * 3 + 10000;
  let iterations = 0;

  while (remaining > 0 && iterations < maxIterations) {
    iterations++;

    if (!isBusinessHour(current, { timezone, businessStartHour: startHour, businessEndHour: endHour, holidays })) {
      current.setMinutes(current.getMinutes() + 1);
      continue;
    }

    // If this minute is a business minute, it counts toward the remaining budget.
    // After consuming this minute, advance to the next minute boundary
    // (the due date is the END of the last consumed business minute).
    remaining--;
    if (remaining > 0) {
      current.setMinutes(current.getMinutes() + 1);
    }
  }

  // Advance past the last consumed minute
  if (minutes > 0) {
    current.setMinutes(current.getMinutes() + 1);
  }

  return current;
}

/**
 * Build a BusinessCalendarConfig from environment and active holidays.
 */
export function buildCalendarConfig(
  activeHolidays: Date[] = [],
): BusinessCalendarConfig {
  const e = env();
  return {
    timezone: e.APP_TIMEZONE,
    businessStartHour: e.BUSINESS_START_HOUR,
    businessEndHour: e.BUSINESS_END_HOUR,
    holidays: activeHolidays,
  };
}