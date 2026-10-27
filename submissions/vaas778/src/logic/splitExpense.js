/**
 * splitExpense.js — Calculate each participant's share (in paise) for an expense.
 *
 * Returns an object { memberId: shareInPaise, ... }.
 * All amounts in integer paise.
 */

import { rupeesToPaise } from '../utils/currency.js';

/**
 * @typedef {'equal'|'exact'|'percentage'} SplitType
 * @typedef {{ description: string, amountPaise: number, paidBy: string,
 *   participants: string[], splitType: SplitType,
 *   exactAmounts?: Record<string,number>, percentages?: Record<string,number>,
 *   date?: string }} ExpenseInput
 */

/**
 * Calculate shares for an expense. Returns { memberId: paise }.
 * @param {ExpenseInput} expense
 * @returns {Record<string, number>}
 */
export function calculateShares(expense) {
  switch (expense.splitType) {
    case 'equal':
      return splitEqual(expense.amountPaise, expense.participants);
    case 'exact':
      return splitExact(expense.amountPaise, expense.participants, expense.exactAmounts || {});
    case 'percentage':
      return splitPercentage(expense.amountPaise, expense.participants, expense.percentages || {});
    default:
      throw new Error(`Unknown split type: ${expense.splitType}`);
  }
}

/**
 * Equal split: divide total among participants, distribute remainder (in paise)
 * deterministicly to the first N participants alphabetically sorted.
 */
function splitEqual(totalPaise, participants) {
  if (participants.length === 0) {
    throw new Error('Equal split requires at least one participant');
  }
  const base = Math.floor(totalPaise / participants.length);
  const remainder = totalPaise - base * participants.length;

  // Sort deterministically for remainder distribution
  const sorted = [...participants].sort();

  const shares = {};
  for (const pid of sorted) {
    shares[pid] = base;
  }
  // Distribute remaining paise one each to the first `remainder` members
  for (let i = 0; i < remainder; i++) {
    shares[sorted[i]] += 1;
  }
  return shares;
}

/**
 * Exact amount split: each participant pays exactly the specified amount in rupees.
 * The sums must match exactly.
 */
function splitExact(totalPaise, participants, exactAmountsRupees) {
  const shares = {};
  let sumPaise = 0;
  for (const pid of participants) {
    const rupees = exactAmountsRupees[pid];
    if (rupees === undefined || rupees === null) {
      throw new Error(`Missing exact amount for participant: ${pid}`);
    }
    if (typeof rupees !== 'number' || rupees < 0) {
      throw new Error(`Exact amount for ${pid} must be a non-negative number`);
    }
    const paise = rupeesToPaise(rupees);
    shares[pid] = paise;
    sumPaise += paise;
  }
  if (sumPaise !== totalPaise) {
    throw new Error(
      `Exact amounts sum to ₹${(sumPaise / 100).toFixed(2)} but expense total is ₹${(totalPaise / 100).toFixed(2)}`,
    );
  }
  return shares;
}

/**
 * Percentage split: each participant pays the specified percentage of the total.
 * Percentages must sum to 100 (tolerance: 0.01).
 * Rounding remainders are assigned deterministically to the largest fractional remainders.
 */
function splitPercentage(totalPaise, participants, percentages) {
  if (participants.length === 0) {
    throw new Error('Percentage split requires at least one participant');
  }

  // Validate sum ≈ 100
  let sumPct = 0;
  for (const pid of participants) {
    const pct = percentages[pid];
    if (pct === undefined || pct === null) {
      throw new Error(`Missing percentage for participant: ${pid}`);
    }
    if (typeof pct !== 'number' || pct < 0 || pct > 100) {
      throw new Error(`Percentage for ${pid} must be between 0 and 100`);
    }
    sumPct += pct;
  }
  if (Math.abs(sumPct - 100) > 0.001) {
    throw new Error(`Percentages sum to ${sumPct}%, must sum to 100%`);
  }

  // Calculate each share with fractional paise, then assign remainders
  const raw = [];
  let assignedPaise = 0;
  for (const pid of participants) {
    const exact = (percentages[pid] / 100) * totalPaise;
    const floor = Math.floor(exact);
    const frac = exact - floor;
    raw.push({ pid, floor, frac });
    assignedPaise += floor;
  }

  const remainder = totalPaise - assignedPaise;

  // Sort by fractional part descending for largest-remainder method
  // Break ties by participant ID for determinism
  raw.sort((a, b) => b.frac - a.frac || a.pid.localeCompare(b.pid));

  const shares = {};
  for (let i = 0; i < raw.length; i++) {
    shares[raw[i].pid] = raw[i].floor + (i < remainder ? 1 : 0);
  }
  return shares;
}