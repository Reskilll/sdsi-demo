/**
 * History tracking for expense operations.
 * Persisted per-user in localStorage.
 */

import type { ExpenseHistoryEntry } from './auth-types';
import { getCurrentUser } from './auth';

const HISTORY_PREFIX = 'splitsage_history_';

function getUserHistoryKey(): string | null {
  const user = getCurrentUser();
  if (!user) return null;
  return `${HISTORY_PREFIX}${user.id}`;
}

export function getHistory(): ExpenseHistoryEntry[] {
  const key = getUserHistoryKey();
  if (!key) return [];
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addHistoryEntry(
  action: ExpenseHistoryEntry['action'],
  description: string,
  details: { expenseCount?: number; memberCount?: number; totalAmount?: number },
): ExpenseHistoryEntry | null {
  const key = getUserHistoryKey();
  const user = getCurrentUser();
  if (!key || !user) return null;

  const entry: ExpenseHistoryEntry = {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    action,
    description,
    details: description,
    expenseCount: details.expenseCount ?? 0,
    memberCount: details.memberCount ?? 0,
    totalAmount: details.totalAmount ?? 0,
    userId: user.id,
  };

  const history = getHistory();
  // Keep last 500 entries max to prevent localStorage bloat
  const updated = [entry, ...history].slice(0, 500);
  localStorage.setItem(key, JSON.stringify(updated));

  return entry;
}

export function clearHistory(): void {
  const key = getUserHistoryKey();
  if (!key) return;
  localStorage.setItem(key, JSON.stringify([]));
}

export function deleteHistoryEntry(entryId: string): void {
  const key = getUserHistoryKey();
  if (!key) return;
  const history = getHistory().filter((e) => e.id !== entryId);
  localStorage.setItem(key, JSON.stringify(history));
}

/**
 * Export all history for the current user as JSON string.
 */
export function exportHistory(): string {
  const entries = getHistory();
  return JSON.stringify(
    entries.map(({ userId, ...rest }) => rest),
    null,
    2,
  );
}