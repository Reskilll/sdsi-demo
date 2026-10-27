'use client';

import { useCallback, useRef, useState } from 'react';
import type { Expense, Member, SettlementResult, SplitType } from '@/lib/types';

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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  // ---- State ----
  const [members, setMembers] = useState([
    { id: newId(), name: 'Alice' },
    { id: newId(), name: 'Bob' },
  ]);

  const [expenses, setExpenses] = useState<Expense[]>([]);

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

  const fileRef = useRef<HTMLInputElement>(null);

  // ---- Member management ----
  const addMember = useCallback(() => {
    const name = prompt('Member name:');
    if (name?.trim()) {
      setMembers((prev) => [...prev, { id: newId(), name: name.trim() }]);
    }
  }, []);

  const removeMember = useCallback((id: string) => {
    setMembers((prev) => prev.filter((m) => m.id !== id));
    // Also remove this member from any split selections
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
  }, []);

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

    const parsed = parseFloat(total);
    if (!desc.trim() || !total || isNaN(parsed) || parsed <= 0 || !paidBy) {
      setErrors(['Fill all fields: description, valid total, and payer.']);
      return;
    }

    let split;
    const netTotal = Math.round(parsed * 100) / 100;

    if (splitType === 'equal') {
      if (equalIds.length === 0) {
        setErrors(['Select at least one share-holder for equal split.']);
        return;
      }
      split = { type: 'equal' as const, shareHolderIds: equalIds };
    } else if (splitType === 'exact') {
      const shares: Record<string, number> = {};
      let sum = 0;
      for (const [id, v] of Object.entries(exactShares)) {
        const n = parseFloat(v);
        if (!isNaN(n) && n >= 0) {
          shares[id] = Math.round(n * 100) / 100;
          sum += shares[id];
        }
      }
      if (Object.keys(shares).length === 0) {
        setErrors(['Enter at least one exact amount.']);
        return;
      }
      sum = Math.round(sum * 100) / 100;
      if (Math.abs(sum - netTotal) > 0.001) {
        setErrors([`Exact amounts sum to ${fmt(sum)}, expected ${fmt(netTotal)}.`]);
        return;
      }
      split = { type: 'exact' as const, shares };
    } else {
      const shares: Record<string, number> = {};
      let sum = 0;
      for (const [id, v] of Object.entries(pctShares)) {
        const n = parseFloat(v);
        if (!isNaN(n) && n >= 0) {
          shares[id] = Math.round(n * 100) / 100;
          sum += shares[id];
        }
      }
      if (Object.keys(shares).length === 0) {
        setErrors(['Enter at least one percentage.']);
        return;
      }
      sum = Math.round(sum * 100) / 100;
      if (Math.abs(sum - 100) > 0.001) {
        setErrors([`Percentages sum to ${sum}%, expected 100%.`]);
        return;
      }
      split = { type: 'percentage' as const, shares };
    }

    const expense: Expense = {
      id: newId(),
      description: desc.trim(),
      total: netTotal,
      paidBy,
      split,
      date: new Date().toISOString().split('T')[0],
    };

    setExpenses((prev) => [...prev, expense]);
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
  ]);

  // ---- Process ----
  const process = useCallback(async () => {
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
        setErrors(
          Array.isArray(json.errors)
            ? json.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`)
            : [json.error ?? 'Unknown error'],
        );
        setResult(null);
      } else {
        setResult(json);
      }
    } catch {
      setErrors(['Network error — could not reach server.']);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [members, expenses]);

  // ---- File upload ----
  const handleFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result as string);
        if (Array.isArray(json.members)) {
          setMembers(
            json.members.map((m: { id?: string; name: string }) => ({
              id: m.id ?? newId(),
              name: m.name,
            })),
          );
        }
        if (Array.isArray(json.expenses)) {
          setExpenses(
            json.expenses.map(
              (
                e: {
                  description: string;
                  total: number;
                  paidBy: string;
                  split: { type: SplitType; shareHolderIds?: string[]; shares?: Record<string, number> };
                  date?: string;
                },
                i: number,
              ) => ({
                ...e,
                id: `file_${i}`,
                date: e.date ?? new Date().toISOString().split('T')[0],
              }),
            ),
          );
        } else {
          // Single expense?
          setExpenses([
            {
              ...(json as Omit<Expense, 'id'>),
              id: 'file_0',
              date: (json as Omit<Expense, 'id'>).date ?? new Date().toISOString().split('T')[0],
            } as Expense,
          ]);
        }
        setErrors([]);
        setResult(null);
      } catch {
        setErrors(['Could not parse JSON file.']);
      }
    };
    reader.readAsText(file);
    // Reset so same file can be re-uploaded
    e.target.value = '';
  }, []);

  // ---- Clear ----
  const clearExpenses = () => {
    setExpenses([]);
    setResult(null);
    setErrors([]);
  };

  // ---- Reset all ----
  const resetAll = () => {
    setMembers([
      { id: newId(), name: 'Alice' },
      { id: newId(), name: 'Bob' },
    ]);
    setExpenses([]);
    setResult(null);
    setErrors([]);
  };

  // ===================================================================
  // Render
  // ===================================================================

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">
          Split<span className="text-primary">Sage</span>
        </h1>
        <p className="text-muted mt-1">
          Expense splitter with minimum-debt settlements
        </p>
      </div>

      {/* ---- Members ---- */}
      <section className="bg-surface-alt border border-border rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Group Members</h2>
          <button
            onClick={addMember}
            className="px-3 py-1.5 text-sm bg-primary hover:bg-primary-dark rounded-lg transition-colors"
          >
            + Add Member
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {members.map((m) => (
            <span
              key={m.id}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded-full text-sm"
            >
              {m.name}
              <button
                onClick={() => removeMember(m.id)}
                className="text-muted hover:text-danger transition-colors"
                aria-label={`Remove ${m.name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </section>

      {/* ---- Add Expense Form ---- */}
      <section className="bg-surface-alt border border-border rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold mb-3">Add Expense</h2>

        {/* Top row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
          <div>
            <label className="block text-sm text-muted mb-1">Description</label>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              placeholder="Dinner at Taj"
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">Total (₹)</label>
            <input
              type="number"
              value={total}
              onChange={(e) => setTotal(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              placeholder="2500"
              min="0.01"
              step="0.01"
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">Paid By</label>
            <select
              value={paidBy}
              onChange={(e) => setPaidBy(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
            >
              <option value="">Select…</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Split type */}
        <div className="flex gap-3 mb-3">
          {(['equal', 'exact', 'percentage'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setSplitType(t)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                splitType === t
                  ? 'bg-primary text-white'
                  : 'bg-surface border border-border text-muted hover:text-white'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* Split details */}
        <div className="bg-surface rounded-lg p-3 mb-3">
          {splitType === 'equal' && (
            <div>
              <p className="text-xs text-muted mb-2">Select who shares this expense:</p>
              <div className="flex flex-wrap gap-2">
                {members.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => toggleEqualId(m.id)}
                    className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                      equalIds.includes(m.id)
                        ? 'bg-primary border-primary text-white'
                        : 'border-border text-muted hover:text-white'
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {splitType === 'exact' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {members.map((m) => (
                <div key={m.id} className="flex items-center gap-2">
                  <span className="text-sm text-muted w-16 shrink-0">{m.name}</span>
                  <input
                    type="number"
                    value={exactShares[m.id] ?? ''}
                    onChange={(e) => setExactShare(m.id, e.target.value)}
                    className="flex-1 bg-surface-alt border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-primary"
                    placeholder="0"
                    min="0"
                    step="0.01"
                  />
                </div>
              ))}
            </div>
          )}

          {splitType === 'percentage' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {members.map((m) => (
                <div key={m.id} className="flex items-center gap-2">
                  <span className="text-sm text-muted w-16 shrink-0">{m.name}</span>
                  <input
                    type="number"
                    value={pctShares[m.id] ?? ''}
                    onChange={(e) => setPctShare(m.id, e.target.value)}
                    className="flex-1 bg-surface-alt border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-primary"
                    placeholder="0"
                    min="0"
                    max="100"
                    step="0.01"
                  />
                  <span className="text-xs text-muted">%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={addExpense}
          className="w-full sm:w-auto px-6 py-2 bg-success hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors"
        >
          Add Expense
        </button>
      </section>

      {/* ---- Expense List ---- */}
      <section className="bg-surface-alt border border-border rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">
            Expenses ({expenses.length})
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => fileRef.current?.click()}
              className="px-3 py-1.5 text-sm bg-surface border border-border rounded-lg hover:border-primary transition-colors"
            >
              📂 Upload JSON
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFile}
            />
            <button
              onClick={clearExpenses}
              className="px-3 py-1.5 text-sm bg-surface border border-border rounded-lg text-muted hover:text-danger transition-colors"
              disabled={expenses.length === 0}
            >
              Clear All
            </button>
          </div>
        </div>

        {expenses.length === 0 ? (
          <p className="text-sm text-muted py-4 text-center">
            No expenses yet. Add one above or upload a JSON file.
          </p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {expenses.map((exp, i) => (
              <div
                key={exp.id}
                className="flex items-center justify-between bg-surface rounded-lg px-4 py-2.5 text-sm"
              >
                <div>
                  <span className="font-medium">{exp.description}</span>
                  <span className="text-muted ml-2">
                    {exp.split.type} · paid by {members.find((m) => m.id === exp.paidBy)?.name ?? exp.paidBy}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono tabular-nums">₹{fmt(exp.total)}</span>
                  <button
                    onClick={() => setExpenses((prev) => prev.filter((_, j) => j !== i))}
                    className="text-muted hover:text-danger transition-colors"
                    aria-label={`Remove ${exp.description}`}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---- Process ---- */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={process}
          disabled={loading || expenses.length === 0}
          className="px-6 py-2.5 bg-primary hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
        >
          {loading ? 'Processing…' : '💡 Settle Up'}
        </button>
        <button
          onClick={resetAll}
          className="px-4 py-2.5 bg-surface border border-border rounded-lg text-sm text-muted hover:text-white transition-colors"
        >
          Reset All
        </button>
      </div>

      {/* ---- Errors ---- */}
      {errors.length > 0 && (
        <section className="bg-red-900/20 border border-danger/30 rounded-xl p-5 mb-6">
          <h2 className="text-danger font-semibold mb-2">Validation Errors</h2>
          <ul className="text-sm space-y-1">
            {errors.map((e, i) => (
              <li key={i} className="text-red-300">
                {e}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ---- Results ---- */}
      {result && (
        <>
          {/* Balances */}
          <section className="bg-surface-alt border border-border rounded-xl p-5 mb-6">
            <h2 className="text-lg font-semibold mb-3">Net Balances</h2>
            <p className="text-xs text-muted mb-3">
              {result.expenseCount} expense{result.expenseCount !== 1 ? 's' : ''}
              {' · '}Total: ₹{fmt(result.totalExpenses)}
              {' · '}Positive = is owed money
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {result.balances.map((b) => (
                <div
                  key={b.memberId}
                  className="flex items-center justify-between bg-surface rounded-lg px-4 py-2.5"
                >
                  <span className="font-medium">{b.name}</span>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-muted">
                      Paid ₹{fmt(b.paid)} · Owed ₹{fmt(b.owed)}
                    </span>
                    <span
                      className={`font-mono font-semibold tabular-nums ${
                        b.net >= 0 ? 'text-success' : 'text-danger'
                      }`}
                    >
                      {b.net >= 0 ? '+' : ''}₹{fmt(b.net)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Settlements */}
          <section className="bg-surface-alt border border-border rounded-xl p-5 mb-6">
            <h2 className="text-lg font-semibold mb-3">
              Simplified Settlements ({result.settlements.length})
            </h2>

            {result.settlements.length === 0 ? (
              <p className="text-sm text-muted py-2">
                🎉 All settled up! Everyone is even.
              </p>
            ) : (
              <div className="space-y-2">
                {result.settlements.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-surface rounded-lg px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-danger">
                        {members.find((m) => m.id === s.from)?.name ?? s.from}
                      </span>
                      <span className="text-muted">pays</span>
                      <span className="font-medium text-success">
                        {members.find((m) => m.id === s.to)?.name ?? s.to}
                      </span>
                    </div>
                    <span className="font-mono font-semibold tabular-nums text-lg">
                      ₹{fmt(s.amount)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}