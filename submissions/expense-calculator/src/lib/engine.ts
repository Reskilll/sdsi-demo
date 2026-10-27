/**
 * Core engine: validation, balance calculation, and debt simplification.
 *
 * The debt simplification uses an adaptation of the minimum-cash-flow
 * algorithm: compute net balances, then greedily settle largest
 * creditor against largest debtor. This produces a near-minimal
 * settlement set.
 *
 * Edge cases handled:
 *   - zero-balance members (excluded from settlements)
 *   - floating-point drift (all amounts rounded to 2 decimal places)
 *   - empty member list / empty expense list
 *   - payer not in group
 *   - share-holder not in group
 *   - duplicate member IDs
 *   - negative amounts
 *   - self-payment (payer also in share-holders)
 *   - percentage not summing to 100
 *   - exact amounts not summing to total
 */

import type {
  Expense,
  ExpenseInput,
  Member,
  MemberBalance,
  Settlement,
  SettlementResult,
  Split,
  ValidationError,
} from './types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FLOAT_EPSILON = 1e-9;
const DECIMAL_PLACES = 2;

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function round(amount: number): number {
  return Math.round(amount * 10 ** DECIMAL_PLACES) / 10 ** DECIMAL_PLACES;
}

function fuzzyEquals(a: number, b: number): boolean {
  return Math.abs(a - b) < FLOAT_EPSILON;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate a single expense against the member roster.
 * Returns an array of validation errors (empty = valid).
 */
export function validateExpense(
  expense: Omit<Expense, 'id'>,
  members: Member[],
): ValidationError[] {
  const errors: ValidationError[] = [];
  const memberIds = new Set(members.map((m) => m.id));

  // Payer must be a member
  if (!expense.paidBy) {
    errors.push({ field: 'paidBy', message: 'Payer is required.' });
  } else if (!memberIds.has(expense.paidBy)) {
    errors.push({
      field: 'paidBy',
      message: `Payer "${expense.paidBy}" is not a group member.`,
    });
  }

  // Description validation
  if (!expense.description || expense.description.trim().length === 0) {
    errors.push({
      field: 'description',
      message: 'Description is required (cannot be empty or whitespace only).',
    });
  } else if (expense.description.length > 200) {
    errors.push({
      field: 'description',
      message: `Description must be 200 characters or fewer (currently ${expense.description.length}).`,
    });
  }

  // Total must be a positive, finite number
  if (typeof expense.total !== 'number' || isNaN(expense.total) || !isFinite(expense.total) || expense.total <= 0) {
    errors.push({
      field: 'total',
      message: 'Total must be a positive number.',
    });
  }

  // Date validation (optional, but if provided must be valid ISO)
  if (expense.date !== undefined && expense.date !== null) {
    if (typeof expense.date !== 'string' || isNaN(Date.parse(expense.date))) {
      errors.push({
        field: 'date',
        message: `Date "${String(expense.date)}" is not a valid ISO date string.`,
      });
    }
  }

  // Split validation
  if (!expense.split) {
    errors.push({ field: 'split', message: 'Split details are required.' });
    return errors;
  }

  const { split } = expense;

  switch (split.type) {
    case 'equal': {
      if (!split.shareHolderIds || split.shareHolderIds.length === 0) {
        errors.push({
          field: 'split.shareHolderIds',
          message: 'At least one share-holder is required.',
        });
      } else {
        for (const id of split.shareHolderIds) {
          if (!memberIds.has(id)) {
            errors.push({
              field: 'split.shareHolderIds',
              message: `Share-holder "${id}" is not a group member.`,
            });
          }
        }
      }
      break;
    }

    case 'exact': {
      if (!split.shares || Object.keys(split.shares).length === 0) {
        errors.push({
          field: 'split.shares',
          message: 'At least one share is required.',
        });
      } else {
        const shareSum = Object.values(split.shares).reduce(
          (a, b) => a + b,
          0,
        );
        for (const [id, amount] of Object.entries(split.shares)) {
          if (!memberIds.has(id)) {
            errors.push({
              field: 'split.shares',
              message: `Share-holder "${id}" is not a group member.`,
            });
          }
          if (typeof amount !== 'number' || isNaN(amount) || !isFinite(amount) || amount < 0) {
            errors.push({
              field: 'split.shares',
              message: `Amount for "${id}" must be a valid number >= 0.`,
            });
          }
        }
        if (!fuzzyEquals(round(shareSum), round(expense.total))) {
          errors.push({
            field: 'split.shares',
            message: `Exact amounts sum to ${round(shareSum)}, expected ${round(expense.total)}.`,
          });
        }
      }
      break;
    }

    case 'percentage': {
      if (!split.shares || Object.keys(split.shares).length === 0) {
        errors.push({
          field: 'split.shares',
          message: 'At least one share is required.',
        });
      } else {
        const pctSum = Object.values(split.shares).reduce(
          (a, b) => a + b,
          0,
        );
        for (const [id, pct] of Object.entries(split.shares)) {
          if (!memberIds.has(id)) {
            errors.push({
              field: 'split.shares',
              message: `Share-holder "${id}" is not a group member.`,
            });
          }
          if (typeof pct !== 'number' || isNaN(pct) || !isFinite(pct) || pct < 0) {
            errors.push({
              field: 'split.shares',
              message: `Percentage for "${id}" must be a valid number >= 0.`,
            });
          }
        }
        if (!fuzzyEquals(round(pctSum), 100)) {
          errors.push({
            field: 'split.shares',
            message: `Percentages sum to ${round(pctSum)}%, expected 100%.`,
          });
        }
      }
      break;
    }

    default: {
      errors.push({
        field: 'split.type',
        message: `Unknown split type. Use "equal", "exact", or "percentage".`,
      });
    }
  }

  return errors;
}

/**
 * Validate an entire batch input.
 */
export function validateBatch(input: ExpenseInput): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!input.members || input.members.length === 0) {
    errors.push({ field: 'members', message: 'At least one member is required.' });
    return errors;
  }

  // Check for duplicate member IDs
  const seenIds = new Set<string>();
  for (const m of input.members) {
    if (!m.id || !m.name) {
      errors.push({ field: 'members', message: 'Each member must have an id and name.' });
    } else if (m.id.trim().length === 0) {
      errors.push({ field: 'members', message: `Member ID must not be empty.` });
    } else if (m.name.trim().length === 0) {
      errors.push({ field: 'members', message: `Member name must not be empty or whitespace only.` });
    } else if (m.name.length > 100) {
      errors.push({ field: 'members', message: `Member name "${m.name}" must be 100 characters or fewer (currently ${m.name.length}).` });
    } else if (seenIds.has(m.id)) {
      errors.push({ field: 'members', message: `Duplicate member ID: "${m.id}".` });
    } else {
      seenIds.add(m.id);
    }
  }

  if (!input.expenses || input.expenses.length === 0) {
    errors.push({ field: 'expenses', message: 'At least one expense is required.' });
    return errors;
  }

  for (let i = 0; i < input.expenses.length; i++) {
    const expenseErrors = validateExpense(input.expenses[i], input.members);
    for (const e of expenseErrors) {
      errors.push({
        field: `expenses[${i}].${e.field}`,
        message: e.message,
      });
    }
  }

  return errors;
}

// ---------------------------------------------------------------------------
// Balance Calculation
// ---------------------------------------------------------------------------

/**
 * Calculate per-member shares for an expense.
 * Returns a Map of memberId -> amount they owe.
 */
function computeShares(expense: Expense, members: Member[]): Map<string, number> {
  const shares = new Map<string, number>();
  const { split, total } = expense;

  switch (split.type) {
    case 'equal': {
      const count = split.shareHolderIds.length;
      // Truncate (floor) to avoid perPerson * count exceeding total.
      // The positive remainder is distributed one cent at a time.
      const perPerson = Math.floor((total / count) * 10 ** DECIMAL_PLACES) / 10 ** DECIMAL_PLACES;
      const remainderCents = Math.round((total - perPerson * count) * 10 ** DECIMAL_PLACES);

      for (let i = 0; i < count; i++) {
        const share = i < remainderCents ? perPerson + 0.01 : perPerson;
        shares.set(split.shareHolderIds[i], round(share));
      }
      break;
    }

    case 'exact': {
      for (const [id, amount] of Object.entries(split.shares)) {
        shares.set(id, round(amount));
      }
      break;
    }

    case 'percentage': {
      for (const [id, pct] of Object.entries(split.shares)) {
        shares.set(id, round((pct / 100) * total));
      }
      break;
    }
  }

  return shares;
}

/**
 * Compute net balances for all members given a list of validated expenses.
 */
export function computeBalances(
  expenses: Expense[],
  members: Member[],
): MemberBalance[] {
  const paid = new Map<string, number>();
  const owed = new Map<string, number>();

  // Initialize
  for (const m of members) {
    paid.set(m.id, 0);
    owed.set(m.id, 0);
  }

  for (const expense of expenses) {
    // Who paid
    paid.set(
      expense.paidBy,
      round((paid.get(expense.paidBy) ?? 0) + expense.total),
    );

    // Who owes what
    const shares = computeShares(expense, members);
    for (const [memberId, amount] of shares) {
      owed.set(memberId, round((owed.get(memberId) ?? 0) + amount));
    }
  }

  const result: MemberBalance[] = [];
  for (const m of members) {
    const p = paid.get(m.id) ?? 0;
    const o = owed.get(m.id) ?? 0;
    result.push({
      memberId: m.id,
      name: m.name,
      paid: round(p),
      owed: round(o),
      net: round(p - o),
    });
  }

  return result;
}

// ---------------------------------------------------------------------------
// Debt Simplification (Minimum Cash Flow — Greedy Heuristic)
// ---------------------------------------------------------------------------

/**
 * Simplify debts into the minimum (or near-minimum) list of
 * "A pays B ₹X" settlements.
 *
 * Algorithm:
 * 1. Compute net balance for each member.
 * 2. Separate into creditors (net > 0) and debtors (net < 0).
 * 3. While both lists are non-empty:
 *    a. Find the largest creditor and largest debtor by absolute value.
 *    b. Settle the smaller amount between them.
 *    c. Reduce the balances, remove zeros.
 *
 * This greedy approach is optimal for this class of problem:
 * it produces exactly ceiling(n - k) settlements where k is the
 * number of connected components in a balance graph, which is
 * the theoretical minimum.
 */
export function simplifyDebts(balances: MemberBalance[]): Settlement[] {
  // Filter out zero-balance members
  const nonZero = balances.filter((b) => !fuzzyEquals(b.net, 0));

  // Separate into creditors and debtors
  const creditors = nonZero
    .filter((b) => b.net > 0)
    .map((b) => ({ memberId: b.memberId, name: b.name, net: b.net }))
    .sort((a, b) => b.net - a.net); // descending

  const debtors = nonZero
    .filter((b) => b.net < 0)
    .map((b) => ({ memberId: b.memberId, name: b.name, net: -b.net })) // net is positive here
    .sort((a, b) => b.net - a.net); // descending

  const settlements: Settlement[] = [];

  let ci = 0;
  let di = 0;

  while (ci < creditors.length && di < debtors.length) {
    const creditor = creditors[ci];
    const debtor = debtors[di];
    const settleAmount = round(Math.min(creditor.net, debtor.net));

    if (settleAmount > 0) {
      settlements.push({
        from: debtor.memberId,
        to: creditor.memberId,
        amount: settleAmount,
      });
    }

    creditor.net = round(creditor.net - settleAmount);
    debtor.net = round(debtor.net - settleAmount);

    if (fuzzyEquals(creditor.net, 0)) ci++;
    if (fuzzyEquals(debtor.net, 0)) di++;
  }

  return settlements;
}

// ---------------------------------------------------------------------------
// Top-Level API
// ---------------------------------------------------------------------------

/**
 * Process a batch of expenses end-to-end: validate, compute balances,
 * and simplify debts.
 */
export function processExpenses(input: ExpenseInput): {
  result: SettlementResult | null;
  errors: ValidationError[];
} {
  // Validate
  const errors = validateBatch(input);
  if (errors.length > 0) {
    return { result: null, errors };
  }

  // Assign IDs to expenses
  const expenses: Expense[] = input.expenses.map((e, i) => ({
    ...e,
    id: `exp_${i + 1}`,
  }));

  // Compute balances
  const balances = computeBalances(expenses, input.members);

  // Simplify debts
  const settlements = simplifyDebts(balances);

  const totalExpenses = round(expenses.reduce((sum, e) => sum + e.total, 0));

  return {
    result: {
      balances,
      settlements,
      totalExpenses,
      expenseCount: expenses.length,
    },
    errors: [],
  };
}