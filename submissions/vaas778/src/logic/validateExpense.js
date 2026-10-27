/**
 * validateExpense.js — Validate an expense input before storing it.
 *
 * Returns { valid: false, errors: string[] } or { valid: true }.
 * All amounts in the expense input are in rupees (float) for human-facing JSON;
 * the expense object carries amountPaise internally.
 */

const VALID_SPLIT_TYPES = new Set(['equal', 'exact', 'percentage']);

/** Maximum expense amount in paise: ₹99,99,99,999 (about 10 crore). */
export const MAX_EXPENSE_PAISE = 999_99_99_999 * 100;

/**
 * @param {{ description: any, amount: any, paidBy: any, participants: any,
 *   splitType: any, exactAmounts?: any, percentages?: any, date?: any,
 *   id?: any }} expense
 * @param {Set<string>} memberIds
 * @param {function(string): boolean} [isDuplicateId] — optional duplicate check
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateExpense(expense, memberIds, isDuplicateId) {
  const errors = [];
  const add = (msg) => errors.push(msg);

  // Description
  if (typeof expense.description !== 'string' || expense.description.trim() === '') {
    add('Description must not be empty.');
  }

  // Amount
  const amount = Number(expense.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    add('Amount must be a positive number.');
  } else if (Math.round(amount * 100) > MAX_EXPENSE_PAISE) {
    add(`Amount exceeds maximum of ₹${(MAX_EXPENSE_PAISE / 100).toLocaleString('en-IN')}.`);
  }
  const amountPaise = Number.isFinite(amount) ? Math.round(amount * 100) : 0;

  // Payer
  if (typeof expense.paidBy !== 'string' || expense.paidBy.trim() === '') {
    add('Payer is required.');
  } else if (!memberIds.has(expense.paidBy)) {
    add(`Payer "${expense.paidBy}" is not a group member.`);
  }

  // Participants
  if (!Array.isArray(expense.participants) || expense.participants.length === 0) {
    add('At least one participant is required.');
  } else {
    const seen = new Set();
    for (const pid of expense.participants) {
      if (typeof pid !== 'string' || pid.trim() === '') {
        add('Participant ID must be a non-empty string.');
      } else if (!memberIds.has(pid)) {
        add(`Participant "${pid}" is not a group member.`);
      } else if (seen.has(pid)) {
        add(`Duplicate participant: "${pid}".`);
      }
      seen.add(pid);
    }
  }

  // Split type
  if (!VALID_SPLIT_TYPES.has(expense.splitType)) {
    add(`Split type must be one of: ${[...VALID_SPLIT_TYPES].join(', ')}.`);
  }

  // Split-specific validation (only if participants and type are valid so far)
  const participants = Array.isArray(expense.participants) ? expense.participants : [];
  if (VALID_SPLIT_TYPES.has(expense.splitType) && participants.length > 0) {
    if (expense.splitType === 'exact') {
      if (!expense.exactAmounts || typeof expense.exactAmounts !== 'object') {
        add('Exact split requires exactAmounts mapping.');
      } else {
        let sum = 0;
        for (const pid of participants) {
          const val = Number(expense.exactAmounts[pid]);
          if (!Number.isFinite(val) || val < 0) {
            add(`Exact amount for "${pid}" must be a non-negative number.`);
          } else {
            sum += Math.round(val * 100);
          }
        }
        if (amountPaise > 0 && sum !== amountPaise) {
          add(
            `Exact amounts sum to ₹${(sum / 100).toFixed(2)} but expense total is ₹${(amount / 100).toFixed(2)}.`,
          );
        }
      }
    }
    if (expense.splitType === 'percentage') {
      if (!expense.percentages || typeof expense.percentages !== 'object') {
        add('Percentage split requires percentages mapping.');
      } else {
        let sum = 0;
        for (const pid of participants) {
          const val = Number(expense.percentages[pid]);
          if (!Number.isFinite(val) || val < 0 || val > 100) {
            add(`Percentage for "${pid}" must be between 0 and 100.`);
          } else {
            sum += val;
          }
        }
        if (Math.abs(sum - 100) > 0.001) {
          add(`Percentages sum to ${sum.toFixed(2)}%, must sum to 100%.`);
        }
      }
    }
  }

  // Date (optional)
  if (expense.date !== undefined && expense.date !== null && expense.date !== '') {
    if (typeof expense.date !== 'string' || isNaN(Date.parse(expense.date))) {
      add('Invalid date format. Use YYYY-MM-DD.');
    }
  }

  // Duplicate ID check
  if (expense.id && isDuplicateId && isDuplicateId(expense.id)) {
    add(`An expense with ID "${expense.id}" already exists.`);
  }

  return errors.length === 0 ? { valid: true } : { valid: false, errors };
}