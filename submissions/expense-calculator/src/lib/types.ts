/**
 * Core type definitions for the Expense Splitter.
 */

/** A person participating in group expenses */
export interface Member {
  id: string;
  name: string;
}

/**
 * How an expense is split among participants.
 * - equal: total divided evenly among shareHolders
 * - exact: each shareHolder pays a specific amount
 * - percentage: each shareHolder pays a percentage of total
 */
export type SplitType = 'equal' | 'exact' | 'percentage';

export interface EqualSplit {
  type: 'equal';
  shareHolderIds: string[]; // who shares the expense
}

export interface ExactSplit {
  type: 'exact';
  shares: Record<string, number>; // memberId -> exact amount they owe
}

export interface PercentageSplit {
  type: 'percentage';
  shares: Record<string, number>; // memberId -> percentage (e.g. 33.33)
}

export type Split = EqualSplit | ExactSplit | PercentageSplit;

/** A single expense entry */
export interface Expense {
  id: string;
  description: string;
  total: number;          // total amount in smallest currency unit (paise/cents) or decimal
  paidBy: string;         // memberId of payer
  split: Split;
  date?: string;          // ISO date string
}

/** A settlement instruction: "from pays to ₹amount" */
export interface Settlement {
  from: string;   // memberId of payer
  to: string;     // memberId of payee
  amount: number;
}

/** Per-member balance summary */
export interface MemberBalance {
  memberId: string;
  name: string;
  paid: number;     // total this member paid (as payer)
  owed: number;     // total this member owes (as share-holder)
  net: number;      // positive = is owed money, negative = owes money
}

/** Result of processing a set of expenses */
export interface SettlementResult {
  balances: MemberBalance[];
  settlements: Settlement[];
  totalExpenses: number;
  expenseCount: number;
}

/** Validation error */
export interface ValidationError {
  field: string;
  message: string;
}

/** Batch input format */
export interface ExpenseInput {
  members: Member[];
  expenses: Omit<Expense, 'id'>[];
}