/**
 * importExpenses.js — Parse and validate JSON import of expenses.
 *
 * Supports importing members and expenses from a JSON file.
 * Batch import is atomic: if any expense is invalid, nothing is imported.
 */

import { validateExpense } from './validateExpense.js';
import { calculateShares } from './splitExpense.js';
import { generateId } from '../utils/helpers.js';

/**
 * Expected JSON schema:
 * {
 *   "members": [ { "id": string, "name": string } ],
 *   "expenses": [
 *     {
 *       "id"?: string,
 *       "description": string,
 *       "amount": number (rupees),
 *       "paidBy": string (member id),
 *       "splitType": "equal" | "exact" | "percentage",
 *       "participants": string[],
 *       "exactAmounts"?: { memberId: number },
 *       "percentages"?: { memberId: number },
 *       "date"?: string (YYYY-MM-DD)
 *     }
 *   ]
 * }
 *
 * Unknown top-level keys are ignored. Unknown keys within expense objects are ignored.
 * Missing required fields are rejected.
 */

/**
 * Parse a JSON string into an import payload.
 * @param {string} jsonString
 * @returns {{ members: Array, expenses: Array }} parsed JSON
 * @throws {Error} if JSON is malformed
 */
export function parseImportJSON(jsonString) {
  let data;
  try {
    data = JSON.parse(jsonString);
  } catch (e) {
    throw new Error(`Malformed JSON: ${e.message}`);
  }

  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('JSON root must be an object.');
  }

  if (!Array.isArray(data.members)) {
    throw new Error('"members" must be an array.');
  }

  if (!Array.isArray(data.expenses)) {
    throw new Error('"expenses" must be an array.');
  }

  return { members: data.members, expenses: data.expenses };
}

/**
 * Validate and import members and expenses.
 *
 * @param {{ members: Array, expenses: Array }} importData
 * @param {Array<{ id: string, name: string }>} existingMembers
 * @param {Array<{ id: string }>} existingExpenses
 * @returns {{
 *   members: Array<{ id: string, name: string }>,
 *   expenses: Array<object>,
 *   errors: string[]
 * }}
 */
export function validateImport(importData, existingMembers, existingExpenses) {
  const errors = [];
  const newMembers = [];
  const newExpenses = [];

  // Build set of all known member IDs (existing + newly imported)
  const allMemberIds = new Set(existingMembers.map((m) => m.id));

  // Validate members first
  const importedMemberIds = new Set();
  for (let i = 0; i < importData.members.length; i++) {
    const m = importData.members[i];
    if (!m || typeof m !== 'object') {
      errors.push(`Member at index ${i} is not an object.`);
      continue;
    }
    if (typeof m.id !== 'string' || m.id.trim() === '') {
      errors.push(`Member at index ${i} missing valid "id".`);
      continue;
    }
    if (typeof m.name !== 'string' || m.name.trim() === '') {
      errors.push(`Member "${m.id}" missing valid "name".`);
      continue;
    }
    if (importedMemberIds.has(m.id)) {
      errors.push(`Duplicate member ID in import: "${m.id}".`);
      continue;
    }
    if (allMemberIds.has(m.id)) {
      // Member already exists — OK, skip adding but don't error
      importedMemberIds.add(m.id);
      continue;
    }
    importedMemberIds.add(m.id);
    allMemberIds.add(m.id);
    newMembers.push({ id: m.id, name: m.name.trim() });
  }

  // Validate expenses
  const existingIds = new Set(existingExpenses.map((e) => e.id));
  const importedIds = new Set();

  for (let i = 0; i < importData.expenses.length; i++) {
    const exp = importData.expenses[i];
    if (!exp || typeof exp !== 'object') {
      errors.push(`Expense at index ${i} is not an object.`);
      continue;
    }

    if (exp.id && (importedIds.has(exp.id) || existingIds.has(exp.id))) {
      errors.push(`Duplicate expense ID "${exp.id}" at index ${i}.`);
      continue;
    }
    if (exp.id) {
      importedIds.add(exp.id);
    }

    const validation = validateExpense(exp, allMemberIds);
    if (!validation.valid) {
      for (const err of validation.errors) {
        errors.push(`Expense ${i}${exp.id ? ' (' + exp.id + ')' : ''}: ${err}`);
      }
      continue;
    }

    // Compute shares to verify split calculations work
    const amountPaise = Math.round(Number(exp.amount) * 100);
    const exactAmounts = exp.exactAmounts || {};
    const percentages = exp.percentages || {};

    try {
      calculateShares({
        amountPaise,
        splitType: exp.splitType,
        participants: exp.participants,
        exactAmounts,
        percentages,
      });
    } catch (e) {
      errors.push(`Expense ${i}${exp.id ? ' (' + exp.id + ')' : ''}: ${e.message}`);
      continue;
    }

    newExpenses.push({
      id: exp.id || generateId(),
      description: exp.description.trim(),
      amountPaise,
      paidBy: exp.paidBy,
      splitType: exp.splitType,
      participants: [...exp.participants],
      exactAmounts: { ...exactAmounts },
      percentages: { ...percentages },
      date: exp.date || null,
    });
  }

  return { members: newMembers, expenses: newExpenses, errors };
}

/**
 * Build a sample expenses JSON for the sample-data file.
 */
export function buildSampleData() {
  return {
    members: [
      { id: 'aman', name: 'Aman' },
      { id: 'rahul', name: 'Rahul' },
      { id: 'priya', name: 'Priya' },
      { id: 'neha', name: 'Neha' },
    ],
    expenses: [
      {
        id: 'exp-1',
        description: 'Dinner at Pind Balluchi',
        amount: 2400,
        paidBy: 'aman',
        splitType: 'equal',
        participants: ['aman', 'rahul', 'priya', 'neha'],
        date: '2026-10-25',
      },
      {
        id: 'exp-2',
        description: 'Movie tickets',
        amount: 1200,
        paidBy: 'rahul',
        splitType: 'equal',
        participants: ['rahul', 'priya'],
        date: '2026-10-26',
      },
      {
        id: 'exp-3',
        description: 'Groceries',
        amount: 850,
        paidBy: 'priya',
        splitType: 'exact',
        participants: ['aman', 'priya', 'neha'],
        exactAmounts: { aman: 300, priya: 250, neha: 300 },
        date: '2026-10-27',
      },
      {
        id: 'exp-4',
        description: 'Cab fare',
        amount: 500,
        paidBy: 'neha',
        splitType: 'percentage',
        participants: ['aman', 'rahul', 'neha'],
        percentages: { aman: 40, rahul: 40, neha: 20 },
        date: '2026-10-27',
      },
    ],
  };
}