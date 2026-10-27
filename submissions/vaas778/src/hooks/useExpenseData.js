/**
 * useExpenseData.js — Central data hook for the expense splitter app.
 *
 * Manages: members, expenses, derived balances, settlements.
 * All persistence via localStorage.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { calculateShares } from '../logic/splitExpense.js';
import { calculateBalances } from '../logic/calculateBalances.js';
import { simplifyDebts, verifySettlements } from '../logic/simplifyDebts.js';
import { generateId } from '../utils/helpers.js';

const STORAGE_KEY_MEMBERS = 'expense-splitter-members';
const STORAGE_KEY_EXPENSES = 'expense-splitter-expenses';

function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {
    // Corrupted data — clear and fall back
    localStorage.removeItem(key);
  }
  return fallback;
}

function saveToStorage(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    // Storage full or unavailable — log but don't crash
    console.error('Failed to save to localStorage:', e);
  }
}

export function useExpenseData() {
  const [members, setMembers] = useState(() => loadFromStorage(STORAGE_KEY_MEMBERS, []));
  const [rawExpenses, setRawExpenses] = useState(() => loadFromStorage(STORAGE_KEY_EXPENSES, []));

  // Persist on change
  useEffect(() => {
    saveToStorage(STORAGE_KEY_MEMBERS, members);
  }, [members]);

  useEffect(() => {
    saveToStorage(STORAGE_KEY_EXPENSES, rawExpenses);
  }, [rawExpenses]);

  // Derive expenses with pre-computed shares
  const expenses = useMemo(() => {
    return rawExpenses.map((exp) => {
      try {
        const shares = calculateShares(exp);
        return { ...exp, shares };
      } catch {
        // Shouldn't happen for stored expenses, but be defensive
        return { ...exp, shares: {} };
      }
    });
  }, [rawExpenses]);

  // Derive balances
  const balances = useMemo(() => calculateBalances(members, expenses), [members, expenses]);

  // Derive settlements
  const settlements = useMemo(() => simplifyDebts(balances), [balances]);

  // Members
  const addMember = useCallback((name) => {
    const trimmed = name.trim();
    if (!trimmed) return { error: 'Name must not be empty.' };
    const id = trimmed.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    if (!id) return { error: 'Name must contain valid characters.' };
    setMembers((prev) => {
      if (prev.some((m) => m.id === id)) {
        return prev; // Silently ignore duplicate ID; caller can check
      }
      return [...prev, { id, name: trimmed }];
    });
    return { success: true };
  }, []);

  const removeMember = useCallback((memberId) => {
    setMembers((prev) => {
      const member = prev.find((m) => m.id === memberId);
      if (!member) return prev;

      // Check if member is referenced in any expense
      const isReferenced = rawExpenses.some(
        (e) =>
          e.paidBy === memberId || e.participants.includes(memberId),
      );
      if (isReferenced) {
        return prev; // Don't remove — UI should handle the message
      }
      return prev.filter((m) => m.id !== memberId);
    });
    return { blocked: false };
  }, [rawExpenses]);

  const isMemberReferenced = useCallback(
    (memberId) => {
      return rawExpenses.some(
        (e) => e.paidBy === memberId || e.participants.includes(memberId),
      );
    },
    [rawExpenses],
  );

  // Expenses
  const addExpense = useCallback((expenseInput) => {
    const amount = Number(expenseInput.amount);
    const amountPaise = Math.round(amount * 100);

    const expense = {
      id: generateId(),
      description: expenseInput.description.trim(),
      amountPaise,
      paidBy: expenseInput.paidBy,
      splitType: expenseInput.splitType,
      participants: [...expenseInput.participants],
      exactAmounts: expenseInput.exactAmounts ? { ...expenseInput.exactAmounts } : {},
      percentages: expenseInput.percentages ? { ...expenseInput.percentages } : {},
      date: expenseInput.date || null,
    };

    // Validate shares compute
    try {
      calculateShares(expense);
    } catch (e) {
      return { error: e.message };
    }

    setRawExpenses((prev) => [...prev, expense]);
    return { success: true };
  }, []);

  const deleteExpense = useCallback((expenseId) => {
    setRawExpenses((prev) => prev.filter((e) => e.id !== expenseId));
  }, []);

  // Import
  const importData = useCallback((newMembers, newExpenses) => {
    setMembers((prev) => {
      const existingIds = new Set(prev.map((m) => m.id));
      const toAdd = newMembers.filter((m) => !existingIds.has(m.id));
      return [...prev, ...toAdd];
    });
    setRawExpenses((prev) => [...prev, ...newExpenses]);
  }, []);

  const resetAll = useCallback(() => {
    setMembers([]);
    setRawExpenses([]);
  }, []);

  const memberMap = useMemo(() => {
    const map = {};
    for (const m of members) {
      map[m.id] = m.name;
    }
    return map;
  }, [members]);

  return {
    members,
    expenses,
    balances,
    settlements,
    memberMap,
    addMember,
    removeMember,
    isMemberReferenced,
    addExpense,
    deleteExpense,
    importData,
    resetAll,
    memberCount: members.length,
    expenseCount: rawExpenses.length,
    settlementCount: settlements.length,
    totalExpenseAmount: expenses.reduce((sum, e) => sum + e.amountPaise, 0),
  };
}