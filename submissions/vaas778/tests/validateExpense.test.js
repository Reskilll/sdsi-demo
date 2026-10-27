import { describe, it, expect } from 'vitest';
import { validateExpense } from '../src/logic/validateExpense.js';

const memberIds = new Set(['aman', 'rahul', 'priya']);

describe('validateExpense', () => {
  it('accepts a valid equal-split expense', () => {
    const result = validateExpense(
      {
        description: 'Dinner',
        amount: 1500,
        paidBy: 'aman',
        splitType: 'equal',
        participants: ['aman', 'rahul', 'priya'],
      },
      memberIds,
    );
    expect(result.valid).toBe(true);
  });

  it('rejects empty description', () => {
    const result = validateExpense(
      { description: '', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('Description'))).toBe(true);
  });

  it('rejects negative amount', () => {
    const result = validateExpense(
      { description: 'Test', amount: -50, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('positive'))).toBe(true);
  });

  it('rejects zero amount', () => {
    const result = validateExpense(
      { description: 'Test', amount: 0, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
  });

  it('rejects unknown payer', () => {
    const result = validateExpense(
      { description: 'Test', amount: 100, paidBy: 'nonexistent', splitType: 'equal', participants: ['aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('not a group member'))).toBe(true);
  });

  it('rejects unknown participant', () => {
    const result = validateExpense(
      { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman', 'ghost'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('ghost'))).toBe(true);
  });

  it('rejects duplicate participants', () => {
    const result = validateExpense(
      { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman', 'aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('Duplicate'))).toBe(true);
  });

  it('rejects empty participants', () => {
    const result = validateExpense(
      { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal', participants: [] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('participant'))).toBe(true);
  });

  it('rejects invalid split type', () => {
    const result = validateExpense(
      { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'bogus', participants: ['aman'] },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('Split type'))).toBe(true);
  });

  it('validates exact split amounts match total', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 1000, paidBy: 'aman', splitType: 'exact',
        participants: ['aman', 'rahul'],
        exactAmounts: { aman: 400, rahul: 500 },
      },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('sum to'))).toBe(true);
  });

  it('validates exact amounts are non-negative', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 1000, paidBy: 'aman', splitType: 'exact',
        participants: ['aman', 'rahul'],
        exactAmounts: { aman: -100, rahul: 1100 },
      },
      memberIds,
    );
    expect(result.valid).toBe(false);
  });

  it('validates percentage sum', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 1000, paidBy: 'aman', splitType: 'percentage',
        participants: ['aman', 'rahul'],
        percentages: { aman: 60, rahul: 30 },
      },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('Percentages sum'))).toBe(true);
  });

  it('validates percentage range', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 1000, paidBy: 'aman', splitType: 'percentage',
        participants: ['aman'],
        percentages: { aman: 200 },
      },
      memberIds,
    );
    expect(result.valid).toBe(false);
  });

  it('rejects malformed date', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal',
        participants: ['aman'], date: 'not-a-date',
      },
      memberIds,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('date'))).toBe(true);
  });

  it('accepts valid date', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal',
        participants: ['aman'], date: '2026-10-27',
      },
      memberIds,
    );
    expect(result.valid).toBe(true);
  });

  it('accepts missing date', () => {
    const result = validateExpense(
      {
        description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal',
        participants: ['aman'],
      },
      memberIds,
    );
    expect(result.valid).toBe(true);
  });

  it('rejects duplicate expense ID', () => {
    const dupCheck = (id) => id === 'dup-1';
    const result = validateExpense(
      {
        id: 'dup-1', description: 'Test', amount: 100, paidBy: 'aman',
        splitType: 'equal', participants: ['aman'],
      },
      memberIds,
      dupCheck,
    );
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes('already exists'))).toBe(true);
  });
});