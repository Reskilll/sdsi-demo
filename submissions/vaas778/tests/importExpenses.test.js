import { describe, it, expect } from 'vitest';
import { parseImportJSON, validateImport } from '../src/logic/importExpenses.js';

describe('importExpenses — parseImportJSON', () => {
  it('parses valid JSON', () => {
    const json = JSON.stringify({
      members: [{ id: 'a', name: 'Alice' }],
      expenses: [],
    });
    const result = parseImportJSON(json);
    expect(result.members).toHaveLength(1);
    expect(result.expenses).toHaveLength(0);
  });

  it('rejects malformed JSON', () => {
    expect(() => parseImportJSON('not json')).toThrow('Malformed JSON');
  });

  it('rejects JSON array root', () => {
    expect(() => parseImportJSON('[]')).toThrow('must be an object');
  });

  it('rejects missing members array', () => {
    expect(() => parseImportJSON('{}')).toThrow('members');
  });

  it('rejects missing expenses array', () => {
    expect(() =>
      parseImportJSON(JSON.stringify({ members: [] })),
    ).toThrow('expenses');
  });
});

describe('importExpenses — validateImport', () => {
  const existingMembers = [{ id: 'aman', name: 'Aman' }];
  const existingExpenses = [];

  it('accepts a valid single expense import', () => {
    const data = {
      members: [{ id: 'rahul', name: 'Rahul' }],
      expenses: [
        {
          description: 'Dinner',
          amount: 1500,
          paidBy: 'aman',
          splitType: 'equal',
          participants: ['aman', 'rahul'],
        },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors).toHaveLength(0);
    expect(result.members).toHaveLength(1);
    expect(result.expenses).toHaveLength(1);
  });

  it('accepts batch import with multiple expenses', () => {
    const data = {
      members: [{ id: 'rahul', name: 'Rahul' }, { id: 'priya', name: 'Priya' }],
      expenses: [
        { description: 'A', amount: 500, paidBy: 'aman', splitType: 'equal', participants: ['aman', 'rahul'] },
        { description: 'B', amount: 300, paidBy: 'rahul', splitType: 'equal', participants: ['rahul', 'priya'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors).toHaveLength(0);
    expect(result.expenses).toHaveLength(2);
  });

  it('rejects batch with one invalid expense', () => {
    const data = {
      members: [],
      expenses: [
        { description: 'Valid', amount: 500, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
        { description: '', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('rejects import with unknown payer', () => {
    const data = {
      members: [],
      expenses: [
        { description: 'Test', amount: 100, paidBy: 'ghost', splitType: 'equal', participants: ['ghost'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.errors[0]).toContain('ghost');
  });

  it('rejects import with unknown participant', () => {
    const data = {
      members: [],
      expenses: [
        { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman', 'ghost'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('rejects duplicate member IDs in import', () => {
    const data = {
      members: [
        { id: 'dup', name: 'First' },
        { id: 'dup', name: 'Second' },
      ],
      expenses: [],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('rejects invalid member objects', () => {
    const data = {
      members: [null, { name: 'No ID' }],
      expenses: [],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBe(2);
  });

  it('skips members that already exist', () => {
    const data = {
      members: [{ id: 'aman', name: 'Aman Duplicate' }],
      expenses: [],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.members).toHaveLength(0); // Already exists
  });

  it('rejects duplicate expense IDs in import', () => {
    const data = {
      members: [],
      expenses: [
        { id: 'dup-exp', description: 'A', amount: 100, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
        { id: 'dup-exp', description: 'B', amount: 200, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('rejects import with invalid split type', () => {
    const data = {
      members: [],
      expenses: [
        { description: 'Test', amount: 100, paidBy: 'aman', splitType: 'bogus', participants: ['aman'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('rejects import with negative amount', () => {
    const data = {
      members: [],
      expenses: [
        { description: 'Test', amount: -100, paidBy: 'aman', splitType: 'equal', participants: ['aman'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('accepts import with new members referenced in expenses', () => {
    const data = {
      members: [{ id: 'neha', name: 'Neha' }],
      expenses: [
        { description: 'Lunch', amount: 800, paidBy: 'neha', splitType: 'equal', participants: ['aman', 'neha'] },
      ],
    };
    const result = validateImport(data, existingMembers, existingExpenses);
    expect(result.errors).toHaveLength(0);
    expect(result.members).toHaveLength(1);
    expect(result.expenses).toHaveLength(1);
  });
});