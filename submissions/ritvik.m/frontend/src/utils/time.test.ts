import { describe, expect, it } from 'vitest';
import {
  addDays,
  combineDateTime,
  formatDate,
  formatDateTimeRange,
  formatDuration,
  formatTime,
  formatTimeRange,
  minutesFromOpen,
  minutesOfDay,
  overlaps,
  roundToStep,
  validateWindow,
  weekdayOf,
} from './time';

describe('wall-clock formatting', () => {
  it('never shifts 10:00 into another timezone', () => {
    expect(formatTime('2026-11-02T10:00:00')).toBe('10:00');
    expect(formatTime('2026-11-02T23:05:00')).toBe('23:05');
    expect(formatTime('10:00:00')).toBe('10:00');
    expect(formatTimeRange('2026-11-02T10:00:00', '2026-11-02T11:30:00')).toBe(
      '10:00\u201311:30',
    );
  });

  it('formats dates from string parts without a Date display conversion', () => {
    expect(formatDate('2026-11-02')).toBe('Mon 2 Nov 2026');
    expect(formatDate('2026-11-02', 'long')).toBe('Monday 2 November 2026');
    expect(formatDateTimeRange('2026-11-02T10:00:00', '2026-11-02T11:00:00')).toBe(
      'Mon 2 Nov 2026 \u00b7 10:00\u201311:00',
    );
  });

  it('formats durations for humans', () => {
    expect(formatDuration(45)).toBe('45 min');
    expect(formatDuration(60)).toBe('1 h');
    expect(formatDuration(90)).toBe('1 h 30 min');
  });
});

describe('minutes from 09:00', () => {
  it('counts from opening time rather than midnight', () => {
    expect(minutesFromOpen('2026-11-02T09:00:00')).toBe(0);
    expect(minutesFromOpen('2026-11-02T10:30:00')).toBe(90);
    expect(minutesFromOpen('2026-11-02T17:45:00')).toBe(525);
    expect(minutesFromOpen('08:30:00')).toBe(-30);
    expect(minutesOfDay('18:00:00')).toBe(1080);
  });
});

describe('overlap', () => {
  it('uses half-open intervals so back-to-back bookings do not conflict', () => {
    expect(
      overlaps(
        '2026-11-02T10:00:00',
        '2026-11-02T11:00:00',
        '2026-11-02T10:30:00',
        '2026-11-02T11:30:00',
      ),
    ).toBe(true);
    expect(
      overlaps(
        '2026-11-02T10:00:00',
        '2026-11-02T11:00:00',
        '2026-11-02T11:00:00',
        '2026-11-02T12:00:00',
      ),
    ).toBe(false);
  });
});

describe('date addition', () => {
  it('crosses month, year and leap-day boundaries', () => {
    expect(addDays('2026-11-02', 1)).toBe('2026-11-03');
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28');
  });

  it('derives the weekday without timezone drift', () => {
    expect(weekdayOf('2026-11-02')).toBe('MONDAY');
    expect(weekdayOf('2026-11-08')).toBe('SUNDAY');
  });
});

describe('form helpers', () => {
  it('rounds clicks to the nearest quarter hour', () => {
    expect(roundToStep(547, 15)).toBe(540);
    expect(roundToStep(548, 15)).toBe(555);
  });

  it('combines a date and time into the API wall-clock shape', () => {
    expect(combineDateTime('2026-11-02', '10:00')).toBe('2026-11-02T10:00:00');
    expect(combineDateTime('2026-11-02', '10:30:00')).toBe('2026-11-02T10:30:00');
  });

  it('validates office hours locally', () => {
    expect(validateWindow('10:00', '11:00')).toBeNull();
    expect(validateWindow('11:00', '10:00')).toContain('after the start');
    expect(validateWindow('08:45', '10:00')).toContain('09:00 and 18:00');
    expect(validateWindow('17:50', '18:10')).toContain('09:00 and 18:00');
    expect(validateWindow('10:00', '10:05')).toContain('15 minutes');
  });
});
