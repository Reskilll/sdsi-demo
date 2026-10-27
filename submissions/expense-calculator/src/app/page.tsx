'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { Expense, Member, SettlementResult, SplitType } from '@/lib/types';
import { getCurrentUser, logout as authLogout, deleteAccount as authDeleteAccount } from '@/lib/auth';
import { getHistory, addHistoryEntry, clearHistory, deleteHistoryEntry, exportHistory } from '@/lib/history';
import type { AppUser, ExpenseHistoryEntry } from '@/lib/auth-types';
import { useToast } from '@/components/toast-provider';
import LoginForm from '@/components/login-form';

// -- Lucide icons --
import {
  Users,
  UserPlus,
  Receipt,
  Calculator,
  Upload,
  Trash2,
  RotateCcw,
  LogOut,
  UserX,
  History,
  Download,
  Clock,
  ChevronDown,
  ChevronUp,
  PieChart,
  ArrowRightLeft,
  IndianRupee,
  Plus,
  X,
  Split,
  Wallet,
  Equal,
  Hash,
  Percent,
  FileJson,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function newId() {
  return crypto.randomUUID();
}

function fmt(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function fmtDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function fmtDateShort(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric',
      month: 'short',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  // ---- Auth ----
  const [user, setUser] = useState<AppUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    setUser(getCurrentUser());
    setAuthChecked(true);
  }, []);

  const handleLoginSuccess = useCallback(() => {
    setUser(getCurrentUser());
  }, []);

  // ---- Toast ----
  const { success, error: toastError, info } = useToast();

  // ---- State ----
  const [members, setMembers] = useState<Member[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const saved = localStorage.getItem('splitsage_members');
      return saved ? (JSON.parse(saved) as Member[]) : [
        { id: newId(), name: 'Alice' },
        { id: newId(), name: 'Bob' },
      ];
    } catch {
      return [
        { id: newId(), name: 'Alice' },
        { id: newId(), name: 'Bob' },
      ];
    }
  });

  const [expenses, setExpenses] = useState<Expense[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const saved = localStorage.getItem('splitsage_expenses');
      return saved ? (JSON.parse(saved) as Expense[]) : [];
    } catch {
      return [];
    }
  });

  // Persist members & expenses to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('splitsage_members', JSON.stringify(members));
  }, [members]);

  useEffect(() => {
    localStorage.setItem('splitsage_expenses', JSON.stringify(expenses));
  }, [expenses]);

  // Form state
  const [desc, setDesc] = useState('');
  const [total, setTotal] = useState('');
  const [paidBy, setPaidBy] = useState('');
  const [splitType, setSplitType] = useState<SplitType>('equal');
  const [equalIds, setEqualIds] = useState<string[]>([]);
  const [exactShares, setExactShares] = useState<Record<string, string>>({});
  const [pctShares, setPctShares] = useState<Record<string, string>>({});

  // Result
  const [result, setResult] = useState<SettlementResult | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // UI toggles
  const [showHistory, setShowHistory] = useState(false);
  const [historyEntries, setHistoryEntries] = useState<ExpenseHistoryEntry[]>([]);
  const [showAddExpense, setShowAddExpense] = useState(true);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [memberFilter, setMemberFilter] = useState<string | null>(null); // filter settlements by member

  const fileRef = useRef<HTMLInputElement>(null);

  // ---- Member management ----
  const addMember = useCallback(() => {
    const name = prompt('Member name:');
    if (name?.trim()) {
      const trimmed = name.trim();
      if (trimmed.length > 100) {
        toastError('Invalid name', 'Name must be 100 characters or fewer.');
        return;
      }
      setMembers((prev) => {
        if (prev.some((m) => m.name.toLowerCase() === trimmed.toLowerCase())) {
          toastError('Duplicate member', `"${trimmed}" already exists.`);
          return prev;
        }
        return [...prev, { id: newId(), name: trimmed }];
      });
      success('Member added', trimmed);
    }
  }, [success, toastError]);

  const removeMember = useCallback(
    (id: string) => {
      const name = members.find((m) => m.id === id)?.name ?? id;
      // Check if member is payer in any expense
      const hasExpenses = expenses.some((e) => e.paidBy === id);
      if (hasExpenses) {
        if (!confirm(`${name} has paid for expenses. Remove anyway?`)) return;
      }
      setMembers((prev) => prev.filter((m) => m.id !== id));
      setEqualIds((prev) => prev.filter((i) => i !== id));
      setExactShares((prev) => {
        const n = { ...prev };
        delete n[id];
        return n;
      });
      setPctShares((prev) => {
        const n = { ...prev };
        delete n[id];
        return n;
      });
      info('Member removed', name);
    },
    [members, expenses, info],
  );

  // ---- Split helpers ----
  const toggleEqualId = (id: string) =>
    setEqualIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );

  const setExactShare = (id: string, value: string) =>
    setExactShares((prev) => ({ ...prev, [id]: value }));

  const setPctShare = (id: string, value: string) =>
    setPctShares((prev) => ({ ...prev, [id]: value }));

  // ---- Add expense ----
  const addExpense = useCallback(() => {
    setErrors([]);

    // Validate description
    const trimmedDesc = desc.trim();
    if (!trimmedDesc) {
      setErrors(['Description is required.']);
      return;
    }
    if (trimmedDesc.length > 200) {
      setErrors(['Description must be 200 characters or fewer.']);
      return;
    }

    // Validate total
    const parsed = parseFloat(total);
    if (!total || isNaN(parsed) || !isFinite(parsed) || parsed <= 0) {
      setErrors(['Enter a valid positive amount.']);
      return;
    }

    // Validate payer
    if (!paidBy || !members.some((m) => m.id === paidBy)) {
      setErrors(['Select a valid payer.']);
      return;
    }

    const netTotal = Math.round(parsed * 100) / 100;
    let split;

    if (splitType === 'equal') {
      if (equalIds.length === 0) {
        setErrors(['Select at least one share-holder for equal split.']);
        return;
      }
      // Validate all share-holders are group members
      const valid = equalIds.every((id) => members.some((m) => m.id === id));
      if (!valid) {
        setErrors(['Some share-holders are no longer group members.']);
        return;
      }
      split = { type: 'equal' as const, shareHolderIds: equalIds };
    } else if (splitType === 'exact') {
      const shares: Record<string, number> = {};
      let sum = 0;
      for (const [id, v] of Object.entries(exactShares)) {
        const n = parseFloat(v);
        if (!isNaN(n) && isFinite(n) && n >= 0) {
          // Only include if member still exists
          if (members.some((m) => m.id === id)) {
            shares[id] = Math.round(n * 100) / 100;
            sum += shares[id];
          }
        }
      }
      if (Object.keys(shares).length === 0) {
        setErrors(['Enter at least one exact amount.']);
        return;
      }
      sum = Math.round(sum * 100) / 100;
      if (Math.abs(sum - netTotal) > 0.009) {
        setErrors([`Exact amounts sum to ₹${fmt(sum)}, expected ₹${fmt(netTotal)}.`]);
        return;
      }
      split = { type: 'exact' as const, shares };
    } else {
      const shares: Record<string, number> = {};
      let sum = 0;
      for (const [id, v] of Object.entries(pctShares)) {
        const n = parseFloat(v);
        if (!isNaN(n) && isFinite(n) && n >= 0) {
          if (members.some((m) => m.id === id)) {
            shares[id] = Math.round(n * 100) / 100;
            sum += shares[id];
          }
        }
      }
      if (Object.keys(shares).length === 0) {
        setErrors(['Enter at least one percentage.']);
        return;
      }
      sum = Math.round(sum * 100) / 100;
      if (Math.abs(sum - 100) > 0.009) {
        setErrors([`Percentages sum to ${sum}%, expected 100%.`]);
        return;
      }
      split = { type: 'percentage' as const, shares };
    }

    const expense: Expense = {
      id: newId(),
      description: trimmedDesc,
      total: netTotal,
      paidBy,
      split,
      date: new Date().toISOString().split('T')[0],
    };

    setExpenses((prev) => [...prev, expense]);
    success('Expense added', `${trimmedDesc} — ₹${fmt(netTotal)}`);

    // Track history
    addHistoryEntry('create', `Added: ${trimmedDesc}`, {
      expenseCount: expenses.length + 1,
      memberCount: members.length,
      totalAmount: expenses.reduce((s, e) => s + e.total, 0) + netTotal,
    });

    // Reset form
    setDesc('');
    setTotal('');
    setPaidBy('');
    setEqualIds([]);
    setExactShares({});
    setPctShares({});
  }, [
    desc,
    equalIds,
    exactShares,
    paidBy,
    pctShares,
    splitType,
    total,
    members,
    expenses,
    success,
  ]);

  // ---- Process ----
  const process = useCallback(
    async (showToast = true) => {
      setLoading(true);
      setErrors([]);
      try {
        const res = await fetch('/api/expenses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            members: members.map((m) => ({ id: m.id, name: m.name })),
            expenses: expenses.map((e) => ({
              description: e.description,
              total: e.total,
              paidBy: e.paidBy,
              split: e.split,
              date: e.date,
            })),
          }),
        });

        const json = await res.json();
        if (!res.ok) {
          const errorMsgs = Array.isArray(json.errors)
            ? json.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`)
            : [json.error ?? 'Unknown error'];
          setErrors(errorMsgs);
          setResult(null);
          if (showToast) toastError('Settlement failed', errorMsgs[0]);
        } else {
          setResult(json);
          if (showToast) {
            const settleCount = json.settlements?.length ?? 0;
            if (settleCount === 0) {
              success('All settled!', 'Everyone is even — no payments needed.');
            } else {
              success(
                'Settlement calculated',
                `${settleCount} payment${settleCount !== 1 ? 's' : ''} found to settle debts.`,
              );
            }
          }
          // Track history
          addHistoryEntry('settle', `Settled ${expenses.length} expense(s)`, {
            expenseCount: expenses.length,
            memberCount: members.length,
            totalAmount: json.totalExpenses ?? 0,
          });
        }
      } catch {
        const msg = 'Network error — could not reach server.';
        setErrors([msg]);
        setResult(null);
        if (showToast) toastError('Connection failed', msg);
      } finally {
        setLoading(false);
      }
    },
    [members, expenses, success, toastError],
  );

  // ---- File upload ----
  const handleFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      // Reject non-JSON files
      if (!file.name.endsWith('.json')) {
        toastError('Invalid file', 'Only .json files are supported.');
        e.target.value = '';
        return;
      }

      // Reject large files (> 5 MB)
      if (file.size > 5 * 1024 * 1024) {
        toastError('File too large', 'Maximum file size is 5 MB.');
        e.target.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        try {
          const json = JSON.parse(reader.result as string);

          // Validate structure
          if (json === null || typeof json !== 'object') {
            toastError('Invalid JSON', 'File must contain a JSON object.');
            return;
          }

          let importedMembers = members;
          let importedExpenses = expenses;

          if (Array.isArray(json.members) && Array.isArray(json.expenses)) {
            // Batch import
            const newMembers = json.members.map((m: { id?: string; name: string }) => ({
              id: m.id ?? newId(),
              name: String(m.name ?? '').trim(),
            })).filter((m: { name: string }) => m.name.length > 0);

            if (newMembers.length === 0) {
              toastError('No valid members', 'Could not parse any members from the file.');
              return;
            }

            if (newMembers.length > 50) {
              toastError('Too many members', 'Maximum 50 members allowed.');
              return;
            }

            const newExpenses = json.expenses.map(
              (e: {
                description: string;
                total: number;
                paidBy: string;
                split: { type: SplitType; shareHolderIds?: string[]; shares?: Record<string, number> };
                date?: string;
              },
              i: number,
            ) => ({
              ...e,
              id: `file_${i}_${Date.now()}`,
              date: e.date ?? new Date().toISOString().split('T')[0],
            }));

            if (newExpenses.length === 0) {
              toastError('No valid expenses', 'Could not parse any expenses from the file.');
              return;
            }

            if (newExpenses.length > 200) {
              toastError('Too many expenses', 'Maximum 200 expenses per batch.');
              return;
            }

            importedMembers = newMembers;
            importedExpenses = newExpenses;
          } else if (typeof json.description === 'string' && typeof json.total === 'number') {
            // Single expense import
            importedExpenses = [
              ...expenses,
              {
                ...(json as Omit<Expense, 'id'>),
                id: `file_0_${Date.now()}`,
                date: (json as Omit<Expense, 'id'>).date ?? new Date().toISOString().split('T')[0],
              },
            ];
          } else {
            toastError('Unknown format', 'File structure not recognized.');
            return;
          }

          setMembers(importedMembers);
          setExpenses(importedExpenses);
          setErrors([]);
          setResult(null);

          success(
            'Imported successfully',
            `${importedMembers.length} member(s), ${importedExpenses.length} expense(s)`,
          );

          addHistoryEntry('import', `Imported from ${file.name}`, {
            expenseCount: importedExpenses.length,
            memberCount: importedMembers.length,
            totalAmount: importedExpenses.reduce((s: number, e: Expense) => s + e.total, 0),
          });
        } catch {
          toastError('Parse error', 'Could not parse JSON file. Check the format.');
        }
      };
      reader.readAsText(file);
      e.target.value = ''; // allow re-upload
    },
    [members, expenses, success, toastError],
  );

  // ---- Download current state ----
  const downloadJSON = useCallback(() => {
    const data = {
      members: members.map(({ id, name }) => ({ id, name })),
      expenses: expenses.map(({ id, ...rest }) => rest),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `splitsage_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    success('Downloaded', `splitsage_${new Date().toISOString().split('T')[0]}.json`);
  }, [members, expenses, success]);

  // ---- Clear expenses ----
  const clearExpenses = useCallback(() => {
    if (expenses.length === 0) return;
    setExpenses([]);
    setResult(null);
    setErrors([]);
    info('Expenses cleared', 'All expense entries removed.');
    addHistoryEntry('clear', `Cleared ${expenses.length} expense(s)`, {
      expenseCount: 0,
      memberCount: members.length,
      totalAmount: 0,
    });
  }, [expenses.length, members.length, info]);

  // ---- Reset all ----
  const resetAll = useCallback(() => {
    setMembers([
      { id: newId(), name: 'Alice' },
      { id: newId(), name: 'Bob' },
    ]);
    setExpenses([]);
    setResult(null);
    setErrors([]);
    info('Reset complete', 'All members and expenses reset to defaults.');
    addHistoryEntry('reset', 'Reset all data', {
      expenseCount: 0,
      memberCount: 2,
      totalAmount: 0,
    });
  }, [info]);

  // ---- History ----
  const loadHistory = useCallback(() => {
    setHistoryEntries(getHistory());
  }, []);

  useEffect(() => {
    if (showHistory) loadHistory();
  }, [showHistory, loadHistory]);

  // ---- Auth actions ----
  const handleLogout = useCallback(() => {
    authLogout();
    setUser(null);
    setExpenses([]);
    setResult(null);
    setMembers([
      { id: newId(), name: 'Alice' },
      { id: newId(), name: 'Bob' },
    ]);
    success('Logged out', 'See you next time!');
  }, [success]);

  const handleDeleteAccount = useCallback(() => {
    if (!confirm('Delete your account and ALL associated data? This cannot be undone.')) return;
    authDeleteAccount();
    setUser(null);
    setExpenses([]);
    setResult(null);
    setMembers([
      { id: newId(), name: 'Alice' },
      { id: newId(), name: 'Bob' },
    ]);
    success('Account deleted', 'All your data has been removed.');
  }, [success]);

  // ---- Computed ----
  const totalAmount = useMemo(
    () => expenses.reduce((s, e) => s + e.total, 0),
    [expenses],
  );

  const memberNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of members) map.set(m.id, m.name);
    return map;
  }, [members]);

  const filteredSettlements = useMemo(() => {
    if (!result || !memberFilter) return result?.settlements ?? [];
    return result.settlements.filter(
      (s) => s.from === memberFilter || s.to === memberFilter,
    );
  }, [result, memberFilter]);

  // ---- Loading state ----
  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  // ---- Not logged in ----
  if (!user) {
    return <LoginForm onSuccess={handleLoginSuccess} />;
  }

  // ===================================================================
  // Logged-in App
  // ===================================================================

  return (
    <main className="min-h-screen bg-surface">
      {/* ---- Top Navigation Bar ---- */}
      <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center text-white font-bold text-sm">
              {user.avatar}
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight leading-tight">
                Split<span className="text-primary">Sage</span>
              </h1>
              <p className="text-xs text-muted">{user.name}</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {/* History toggle */}
            <button
              onClick={() => setShowHistory((p) => !p)}
              className={`p-2 rounded-xl transition-colors ${
                showHistory ? 'bg-primary text-white' : 'text-muted hover:text-white hover:bg-surface-alt'
              }`}
              title="History"
            >
              <History className="w-5 h-5" />
            </button>

            {/* Download */}
            <button
              onClick={downloadJSON}
              className="p-2 rounded-xl text-muted hover:text-white hover:bg-surface-alt transition-colors"
              title="Download as JSON"
              disabled={expenses.length === 0}
            >
              <Download className="w-5 h-5" />
            </button>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl text-muted hover:text-danger hover:bg-surface-alt transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* ================================================================ */}
        {/* Stats Bar                                                         */}
        {/* ================================================================ */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-surface-alt border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-muted text-xs uppercase tracking-wider mb-1">
              <Users className="w-3.5 h-3.5" />
              Members
            </div>
            <p className="text-2xl font-bold tabular-nums">{members.length}</p>
          </div>

          <div className="bg-surface-alt border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-muted text-xs uppercase tracking-wider mb-1">
              <Receipt className="w-3.5 h-3.5" />
              Expenses
            </div>
            <p className="text-2xl font-bold tabular-nums">{expenses.length}</p>
          </div>

          <div className="bg-surface-alt border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-muted text-xs uppercase tracking-wider mb-1">
              <IndianRupee className="w-3.5 h-3.5" />
              Total Spent
            </div>
            <p className="text-2xl font-bold tabular-nums text-success">₹{fmt(totalAmount)}</p>
          </div>

          <div className="bg-surface-alt border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-muted text-xs uppercase tracking-wider mb-1">
              <ArrowRightLeft className="w-3.5 h-3.5" />
              Settlements
            </div>
            <p className="text-2xl font-bold tabular-nums text-primary">
              {result?.settlements.length ?? '—'}
            </p>
          </div>
        </div>

        {/* ================================================================ */}
        {/* History Panel (collapsible)                                       */}
        {/* ================================================================ */}
        {showHistory && (
          <section className="bg-surface-alt border border-border rounded-2xl overflow-hidden animate-slide-in">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <h2 className="font-semibold flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted" />
                Activity History
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearHistory}
                  className="text-xs text-muted hover:text-danger transition-colors px-2 py-1 rounded"
                >
                  Clear All
                </button>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-muted hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {historyEntries.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-muted">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-40" />
                No activity yet. Start adding expenses!
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto divide-y divide-border">
                {historyEntries.map((entry) => {
                  const actionColors: Record<string, string> = {
                    create: 'text-success',
                    settle: 'text-primary',
                    import: 'text-warning',
                    clear: 'text-muted',
                    reset: 'text-danger',
                  };

                  return (
                    <div
                      key={entry.id}
                      className="flex items-start justify-between px-5 py-3 hover:bg-surface/50 transition-colors"
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <span
                          className={`text-xs font-mono uppercase tracking-wider mt-0.5 ${actionColors[entry.action] ?? 'text-muted'}`}
                        >
                          {entry.action}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm truncate">{entry.description}</p>
                          <p className="text-xs text-muted mt-0.5">
                            {fmtDate(entry.timestamp)}
                            {entry.expenseCount > 0 ? ` · ${entry.expenseCount} exp.` : ''}
                            {entry.totalAmount > 0 ? ` · ₹${fmt(entry.totalAmount)}` : ''}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          deleteHistoryEntry(entry.id);
                          loadHistory();
                        }}
                        className="shrink-0 ml-2 text-muted hover:text-danger transition-colors"
                        aria-label="Delete history entry"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Export history */}
            {historyEntries.length > 0 && (
              <div className="px-5 py-2 border-t border-border">
                <button
                  onClick={() => {
                    const blob = new Blob([exportHistory()], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `splitsage_history_${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                    success('History exported');
                  }}
                  className="text-xs text-primary hover:text-primary-dark transition-colors flex items-center gap-1"
                >
                  <Download className="w-3 h-3" />
                  Export history
                </button>
              </div>
            )}
          </section>
        )}

        {/* ================================================================ */}
        {/* Members Section                                                   */}
        {/* ================================================================ */}
        <section className="bg-surface-alt border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              Group Members
            </h2>
            <button
              onClick={addMember}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary hover:bg-primary-dark rounded-xl font-medium transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {members.map((m) => (
              <span
                key={m.id}
                className="group inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface border border-border rounded-full text-sm transition-colors"
              >
                <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-[10px] font-bold flex items-center justify-center">
                  {m.name[0]?.toUpperCase()}
                </span>
                {m.name}
                <button
                  onClick={() => removeMember(m.id)}
                  className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all"
                  aria-label={`Remove ${m.name}`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
            {members.length === 0 && (
              <p className="text-sm text-muted">Add members to get started.</p>
            )}
          </div>
        </section>

        {/* ================================================================ */}
        {/* Add Expense Section                                               */}
        {/* ================================================================ */}
        <section className="bg-surface-alt border border-border rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowAddExpense((p) => !p)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface/50 transition-colors"
          >
            <h2 className="font-semibold flex items-center gap-2">
              <Plus className="w-5 h-5 text-success" />
              Add Expense
            </h2>
            {showAddExpense ? (
              <ChevronUp className="w-5 h-5 text-muted" />
            ) : (
              <ChevronDown className="w-5 h-5 text-muted" />
            )}
          </button>

          {showAddExpense && (
            <div className="px-5 pb-5 border-t border-border">
              {/* Description + Total + Payer */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 mb-3">
                <div>
                  <label className="block text-xs text-muted mb-1.5">Description</label>
                  <input
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    className="w-full bg-surface border border-border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors"
                    placeholder="Dinner at Taj"
                    maxLength={200}
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted mb-1.5">Amount (₹)</label>
                  <div className="relative">
                    <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                    <input
                      type="number"
                      value={total}
                      onChange={(e) => setTotal(e.target.value)}
                      className="w-full bg-surface border border-border rounded-xl pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors"
                      placeholder="2500"
                      min="0.01"
                      step="0.01"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-muted mb-1.5">Paid By</label>
                  <select
                    value={paidBy}
                    onChange={(e) => setPaidBy(e.target.value)}
                    className="w-full bg-surface border border-border rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors"
                  >
                    <option value="">Select payer…</option>
                    {members.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Split type selector */}
              <div className="flex gap-1.5 mb-3 bg-surface rounded-xl p-1">
                {([
                  { type: 'equal' as const, Icon: Equal, label: 'Equal' },
                  { type: 'exact' as const, Icon: Hash, label: 'Exact' },
                  { type: 'percentage' as const, Icon: Percent, label: 'Percentage' },
                ]).map(({ type, Icon, label }) => (
                  <button
                    key={type}
                    onClick={() => setSplitType(type)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all ${
                      splitType === type
                        ? 'bg-primary text-white shadow'
                        : 'text-muted hover:text-white'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                ))}
              </div>

              {/* Split details */}
              <div className="bg-surface rounded-xl p-4 mb-3">
                {splitType === 'equal' && (
                  <div>
                    <p className="text-xs text-muted mb-2 flex items-center gap-1">
                      <Split className="w-3.5 h-3.5" />
                      Select who shares this expense:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {members.map((m) => (
                        <button
                          key={m.id}
                          onClick={() => toggleEqualId(m.id)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-all ${
                            equalIds.includes(m.id)
                              ? 'bg-primary border-primary text-white'
                              : 'border-border text-muted hover:border-primary hover:text-white'
                          }`}
                        >
                          {m.name}
                        </button>
                      ))}
                    </div>
                    {members.length === 0 && (
                      <p className="text-xs text-muted">Add members first.</p>
                    )}
                    {equalIds.length > 0 && (
                      <p className="text-xs text-muted mt-2">
                        Each person pays ₹{fmt(parseFloat(total || '0') / equalIds.length || 0)}
                        {equalIds.length > 0 && parseFloat(total || '0') > 0 && (
                          <> ({equalIds.length} people)</>
                        )}
                      </p>
                    )}
                  </div>
                )}

                {splitType === 'exact' && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {members.map((m) => (
                      <div key={m.id} className="flex items-center gap-2">
                        <span className="text-sm text-muted w-20 shrink-0 truncate">{m.name}</span>
                        <div className="relative flex-1">
                          <IndianRupee className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted" />
                          <input
                            type="number"
                            value={exactShares[m.id] ?? ''}
                            onChange={(e) => setExactShare(m.id, e.target.value)}
                            className="w-full bg-surface-alt border border-border rounded-lg pl-6 pr-2 py-1.5 text-sm focus:outline-none focus:border-primary transition-colors"
                            placeholder="0"
                            min="0"
                            step="0.01"
                          />
                        </div>
                      </div>
                    ))}
                    {members.length === 0 && (
                      <p className="text-xs text-muted col-span-full">Add members first.</p>
                    )}
                  </div>
                )}

                {splitType === 'percentage' && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {members.map((m) => (
                      <div key={m.id} className="flex items-center gap-2">
                        <span className="text-sm text-muted w-20 shrink-0 truncate">{m.name}</span>
                        <div className="relative flex-1">
                          <input
                            type="number"
                            value={pctShares[m.id] ?? ''}
                            onChange={(e) => setPctShare(m.id, e.target.value)}
                            className="w-full bg-surface-alt border border-border rounded-lg px-2 py-1.5 pr-7 text-sm focus:outline-none focus:border-primary transition-colors"
                            placeholder="0"
                            min="0"
                            max="100"
                            step="0.01"
                          />
                          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted">%</span>
                        </div>
                      </div>
                    ))}
                    {members.length === 0 && (
                      <p className="text-xs text-muted col-span-full">Add members first.</p>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={addExpense}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-success hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Expense
              </button>
            </div>
          )}
        </section>

        {/* ================================================================ */}
        {/* Expense List                                                      */}
        {/* ================================================================ */}
        <section className="bg-surface-alt border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2">
              <Receipt className="w-5 h-5 text-warning" />
              Expenses
              {expenses.length > 0 && (
                <span className="text-sm font-normal text-muted">
                  ({expenses.length})
                </span>
              )}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-surface border border-border rounded-xl hover:border-primary transition-colors text-muted hover:text-white"
              >
                <FileJson className="w-4 h-4" />
                Import
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleFile}
              />
              {expenses.length > 0 && (
                <button
                  onClick={clearExpenses}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-surface border border-border rounded-xl text-muted hover:text-danger hover:border-danger transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {expenses.length === 0 ? (
            <div className="py-12 text-center">
              <Receipt className="w-10 h-10 mx-auto mb-3 text-muted opacity-40" />
              <p className="text-sm text-muted">
                No expenses yet. Add one above or import a JSON file.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {expenses.map((exp, i) => {
                const payerName = memberNameMap.get(exp.paidBy) ?? exp.paidBy;
                const splitDesc =
                  exp.split.type === 'equal'
                    ? `÷ ${exp.split.shareHolderIds.length} people`
                    : exp.split.type === 'percentage'
                      ? '% split'
                      : 'exact split';

                return (
                  <div
                    key={exp.id}
                    className="group flex items-center justify-between bg-surface rounded-xl px-4 py-3 hover:bg-surface/70 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm truncate">{exp.description}</p>
                        <span className="text-[10px] uppercase tracking-wider text-muted bg-surface-alt px-1.5 py-0.5 rounded-full shrink-0">
                          {exp.split.type}
                        </span>
                      </div>
                      <p className="text-xs text-muted mt-0.5">
                        Paid by {payerName} · {splitDesc}
                        {exp.date ? ` · ${fmtDateShort(exp.date)}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 ml-3 shrink-0">
                      <span className="font-mono font-semibold tabular-nums">
                        ₹{fmt(exp.total)}
                      </span>
                      <button
                        onClick={() => {
                          const removed = expenses[i];
                          setExpenses((prev) => prev.filter((_, j) => j !== i));
                          if (result) setResult(null);
                          info('Expense removed', removed.description);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all"
                        aria-label={`Remove ${exp.description}`}
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ================================================================ */}
        {/* Action Bar                                                        */}
        {/* ================================================================ */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => process(true)}
            disabled={loading || expenses.length === 0}
            className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-medium transition-colors shadow-lg shadow-primary/20"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Calculating…
              </>
            ) : (
              <>
                <Calculator className="w-5 h-5" />
                Settle Up
              </>
            )}
          </button>

          <button
            onClick={() => {
              setResult(null);
              setErrors([]);
            }}
            className="px-4 py-3 bg-surface border border-border rounded-xl text-sm text-muted hover:text-white transition-colors"
            disabled={!result}
          >
            Clear Results
          </button>

          <button
            onClick={resetAll}
            className="flex items-center gap-1.5 px-4 py-3 bg-surface border border-border rounded-xl text-sm text-muted hover:text-danger transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset All
          </button>

          {/* Delete account */}
          <button
            onClick={() => setShowConfirmDelete(true)}
            className="flex items-center gap-1.5 px-4 py-3 bg-surface border border-border rounded-xl text-sm text-muted hover:text-danger transition-colors ml-auto"
          >
            <UserX className="w-4 h-4" />
          </button>
        </div>

        {/* Confirm delete account modal */}
        {showConfirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-surface-alt border border-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
              <h3 className="text-lg font-semibold mb-2">Delete Account?</h3>
              <p className="text-sm text-muted mb-6">
                This will permanently delete your account and all associated data. This action cannot be undone.
              </p>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowConfirmDelete(false)}
                  className="px-4 py-2 bg-surface border border-border rounded-xl text-sm hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  className="px-4 py-2 bg-danger hover:bg-red-700 rounded-xl text-sm font-medium transition-colors"
                >
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---- Errors ---- */}
        {errors.length > 0 && (
          <section className="bg-danger/10 border border-danger/30 rounded-2xl p-5 animate-slide-in">
            <h2 className="font-semibold text-danger mb-2 flex items-center gap-2">
              <X className="w-4 h-4" />
              Validation Errors
            </h2>
            <ul className="text-sm space-y-1">
              {errors.map((e, i) => (
                <li key={i} className="text-danger/80">
                  {e}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ================================================================ */}
        {/* Results                                                           */}
        {/* ================================================================ */}
        {result && (
          <div className="space-y-6 animate-slide-in">
            {/* Balances */}
            <section className="bg-surface-alt border border-border rounded-2xl p-5">
              <h2 className="font-semibold mb-1 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-primary" />
                Net Balances
              </h2>
              <p className="text-xs text-muted mb-4">
                {result.expenseCount} expense{result.expenseCount !== 1 ? 's' : ''} · Total: ₹
                {fmt(result.totalExpenses)} · <span className="text-success">+</span> = owed money
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {result.balances.map((b) => (
                  <div
                    key={b.memberId}
                    className={`flex items-center justify-between bg-surface rounded-xl px-4 py-3 border transition-colors ${
                      memberFilter === b.memberId
                        ? 'border-primary ring-1 ring-primary'
                        : 'border-transparent hover:border-border'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-8 h-8 rounded-full bg-primary/20 text-primary font-bold text-xs flex items-center justify-center shrink-0">
                        {b.name[0]?.toUpperCase()}
                      </span>
                      <div className="min-w-0">
                        <p
                          className="font-medium text-sm truncate cursor-pointer"
                          onClick={() =>
                            setMemberFilter((f) => (f === b.memberId ? null : b.memberId))
                          }
                        >
                          {b.name}
                        </p>
                        <p className="text-xs text-muted">
                          Paid ₹{fmt(b.paid)} · Owed ₹{fmt(b.owed)}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`font-mono font-bold tabular-nums text-sm ml-3 shrink-0 ${
                        b.net >= 0 ? 'text-success' : 'text-danger'
                      }`}
                    >
                      {b.net >= 0 ? '+' : ''}₹{fmt(b.net)}
                    </span>
                  </div>
                ))}
              </div>
              {memberFilter && (
                <p className="text-xs text-primary mt-3 flex items-center gap-1">
                  Filtering settlements for{' '}
                  <strong>{memberNameMap.get(memberFilter)}</strong>
                  <button
                    onClick={() => setMemberFilter(null)}
                    className="ml-1 hover:underline"
                  >
                    (clear)
                  </button>
                </p>
              )}
            </section>

            {/* Settlements */}
            <section className="bg-surface-alt border border-border rounded-2xl p-5">
              <h2 className="font-semibold mb-1 flex items-center gap-2">
                <Wallet className="w-5 h-5 text-success" />
                Simplified Settlements
                <span className="text-sm font-normal text-muted">
                  ({result.settlements.length})
                </span>
              </h2>
              <p className="text-xs text-muted mb-4">
                Minimum payment plan to settle all debts
              </p>

              {result.settlements.length === 0 ? (
                <div className="py-10 text-center">
                  <div className="text-4xl mb-2">🎉</div>
                  <p className="text-muted">All settled up! Everyone is even.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredSettlements.map((s, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between bg-surface rounded-xl px-4 py-3.5"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-2">
                          <span className={`font-semibold ${memberFilter === s.from ? 'text-danger' : ''}`}>
                            {memberNameMap.get(s.from) ?? s.from}
                          </span>
                          <ArrowRightLeft className="w-4 h-4 text-muted" />
                          <span className={`font-semibold ${memberFilter === s.to ? 'text-success' : ''}`}>
                            {memberNameMap.get(s.to) ?? s.to}
                          </span>
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-lg tabular-nums">
                          ₹{fmt(s.amount)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {/* ---- Footer ---- */}
        <footer className="text-center text-xs text-muted py-6 border-t border-border">
          SplitSage · {user.name} · {new Date().getFullYear()}
        </footer>
      </div>
    </main>
  );
}