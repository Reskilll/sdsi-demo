import { useState, useCallback } from 'react';
import { useExpenseData } from './hooks/useExpenseData.js';
import {
  SummaryCards, MemberBalances, SettlementList, ExpenseList,
  MemberManager, JsonImport,
} from './components/Dashboard.jsx';
import ExpenseForm from './components/ExpenseForm.jsx';
import { parseImportJSON, validateImport } from './logic/importExpenses.js';
import { calculateShares } from './logic/splitExpense.js';
import './components/Dashboard.css';

export default function App() {
  const {
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
    memberCount,
    expenseCount,
    settlementCount,
    totalExpenseAmount,
  } = useExpenseData();

  const [view, setView] = useState('dashboard'); // 'dashboard' | 'add-expense' | 'members' | 'import'

  const handleImport = useCallback(
    (jsonString) => {
      const parsed = parseImportJSON(jsonString);
      const validation = validateImport(
        parsed,
        members,
        expenses.map((e) => ({ id: e.id })),
      );
      if (validation.errors.length > 0) {
        return { errors: validation.errors };
      }

      // Compute shares for each imported expense
      const readyExpenses = validation.expenses.map((exp) => {
        try {
          const shares = calculateShares(exp);
          return { ...exp, shares };
        } catch (e) {
          validation.errors.push(`${exp.description}: ${e.message}`);
          return null;
        }
      });

      // Check for new errors from share calculation
      const failed = readyExpenses.filter((e) => e === null);
      if (failed.length > 0) {
        return { errors: validation.errors };
      }

      importData(validation.members, readyExpenses);
      return { members: validation.members, expenses: readyExpenses };
    },
    [members, expenses, importData],
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          Expense<span>Splitter</span>
        </h1>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => setView('add-expense')}>
            + Add Expense
          </button>
          <button className="btn btn-secondary" onClick={() => setView('import')}>
            Import JSON
          </button>
          <button className="btn btn-secondary" onClick={() => setView('members')}>
            Members
          </button>
        </div>
      </header>

      {view === 'add-expense' && (
        <ExpenseForm
          members={members}
          memberMap={memberMap}
          onSubmit={(input) => {
            const result = addExpense(input);
            if (result && result.error) return result;
            setView('dashboard');
            return { success: true };
          }}
          onCancel={() => setView('dashboard')}
        />
      )}

      {view === 'members' && (
        <MemberManager
          members={members}
          memberMap={memberMap}
          onAdd={addMember}
          onRemove={removeMember}
          isReferenced={isMemberReferenced}
        />
      )}

      {view === 'import' && <JsonImport onImport={handleImport} />}

      {view === 'dashboard' && (
        <>
          {members.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 48 }}>
              <h2 style={{ margin: '0 0 12px', fontWeight: 600 }}>Welcome to ExpenseSplitter</h2>
              <p style={{ color: 'var(--text-secondary)', margin: '0 0 24px' }}>
                Add members to your group, then start splitting expenses.
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                <button className="btn btn-primary" onClick={() => setView('members')}>
                  Add Members
                </button>
                <button className="btn btn-secondary" onClick={() => setView('import')}>
                  Import from JSON
                </button>
              </div>
            </div>
          ) : (
            <>
              <SummaryCards
                totalAmount={totalExpenseAmount}
                memberCount={memberCount}
                expenseCount={expenseCount}
                settlementCount={settlementCount}
              />
              <div className="dashboard-grid">
                <MemberBalances balances={balances} memberMap={memberMap} />
                <SettlementList settlements={settlements} memberMap={memberMap} />
              </div>
              <ExpenseList
                expenses={[...expenses].reverse()}
                memberMap={memberMap}
                onDelete={deleteExpense}
              />
            </>
          )}
        </>
      )}

      <footer className="app-footer">
        ExpenseSplitter &mdash; PS1 &mdash; Digithon 2026
      </footer>
    </div>
  );
}