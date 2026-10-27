import { useState } from 'react';
import { paiseToRupees, formatSignedBalance } from '../utils/currency.js';
import './Dashboard.css';

export function SummaryCards({ totalAmount, memberCount, expenseCount, settlementCount }) {
  return (
    <div className="summary-cards">
      <div className="card summary-card">
        <span className="card-label">Total Expenses</span>
        <span className="card-value">{paiseToRupees(totalAmount)}</span>
      </div>
      <div className="card summary-card">
        <span className="card-label">Members</span>
        <span className="card-value">{memberCount}</span>
      </div>
      <div className="card summary-card">
        <span className="card-label">Expenses</span>
        <span className="card-value">{expenseCount}</span>
      </div>
      <div className="card summary-card">
        <span className="card-label">Settlements</span>
        <span className="card-value">{settlementCount}</span>
      </div>
    </div>
  );
}

export function MemberBalances({ balances, memberMap }) {
  return (
    <div className="card">
      <h3>Member Balances</h3>
      {balances.length === 0 ? (
        <p className="empty-state">No members yet. Add members to get started.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Member</th>
                <th className="num">Paid</th>
                <th className="num">Owed</th>
                <th className="num">Balance</th>
              </tr>
            </thead>
            <tbody>
              {balances.map((b) => (
                <tr key={b.memberId}>
                  <td>{memberMap[b.memberId] || b.memberId}</td>
                  <td className="num">{paiseToRupees(b.paid)}</td>
                  <td className="num">{paiseToRupees(b.owed)}</td>
                  <td className={`num balance ${b.balance > 0 ? 'positive' : b.balance < 0 ? 'negative' : ''}`}>
                    {formatSignedBalance(b.balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function SettlementList({ settlements, memberMap }) {
  return (
    <div className="card">
      <h3>Settlements</h3>
      {settlements.length === 0 ? (
        <p className="empty-state">All settled up! No payments needed.</p>
      ) : (
        <div className="settlements-list">
          {settlements.map((s, i) => (
            <div key={i} className="settlement-item">
              <span className="settlement-from">{memberMap[s.from] || s.from}</span>
              <span className="settlement-arrow">pays</span>
              <span className="settlement-to">{memberMap[s.to] || s.to}</span>
              <span className="settlement-amount">{paiseToRupees(s.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ExpenseList({ expenses, memberMap, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(null);

  const handleDelete = (id) => {
    onDelete(id);
    setConfirmDelete(null);
  };

  const formatDate = (d) => {
    if (!d) return '-';
    try {
      return new Date(d).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return d;
    }
  };

  const splitLabel = (exp) => {
    switch (exp.splitType) {
      case 'equal': return 'Equal';
      case 'exact': return 'Exact';
      case 'percentage': return 'Percentage';
      default: return exp.splitType;
    }
  };

  return (
    <div className="card">
      <h3>Recent Expenses</h3>
      {expenses.length === 0 ? (
        <p className="empty-state">No expenses yet. Add an expense or import from JSON.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Description</th>
                <th>Paid by</th>
                <th className="num">Amount</th>
                <th>Split</th>
                <th>Participants</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((exp) => (
                <tr key={exp.id}>
                  <td>{exp.description}</td>
                  <td>{memberMap[exp.paidBy] || exp.paidBy}</td>
                  <td className="num">{paiseToRupees(exp.amountPaise)}</td>
                  <td>{splitLabel(exp)}</td>
                  <td>{exp.participants.map((p) => memberMap[p] || p).join(', ')}</td>
                  <td>{formatDate(exp.date)}</td>
                  <td>
                    {confirmDelete === exp.id ? (
                      <span className="confirm-delete">
                        <button className="btn-link danger" onClick={() => handleDelete(exp.id)}>Yes</button>
                        <button className="btn-link" onClick={() => setConfirmDelete(null)}>No</button>
                      </span>
                    ) : (
                      <button className="btn-link danger" onClick={() => setConfirmDelete(exp.id)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function MemberManager({ members, memberMap, onAdd, onRemove, isReferenced }) {
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');

  const handleAdd = (e) => {
    e.preventDefault();
    const result = onAdd(name);
    if (result && result.error) {
      setMessage(result.error);
    } else {
      setName('');
      setMessage('');
    }
  };

  const handleRemove = (id) => {
    const ref = isReferenced(id);
    if (ref) {
      setMessage(`Cannot remove "${memberMap[id] || id}" — they are part of existing expenses. Delete those expenses first.`);
      return;
    }
    onRemove(id);
    setMessage('');
  };

  return (
    <div className="card">
      <h3>Members</h3>
      {message && <div className="form-errors" style={{ marginBottom: 12 }}><p>{message}</p></div>}
      <form className="add-member-form" onSubmit={handleAdd}>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Member name"
        />
        <button type="submit" className="btn btn-primary btn-sm">Add</button>
      </form>
      <div className="member-list">
        {members.map((m) => (
          <div key={m.id} className="member-row">
            <span>{m.name}</span>
            <button className="btn-link danger" onClick={() => handleRemove(m.id)}>Remove</button>
          </div>
        ))}
        {members.length === 0 && <p className="empty-state" style={{ marginTop: 12 }}>No members. Add at least one to start.</p>}
      </div>
    </div>
  );
}

export function JsonImport({ onImport }) {
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState(''); // 'success' | 'error'

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const result = onImport(evt.target.result);
        if (result.errors && result.errors.length > 0) {
          setMessage(`Import failed:\n${result.errors.join('\n')}`);
          setStatus('error');
        } else {
          const m = result.members?.length || 0;
          const x = result.expenses?.length || 0;
          setMessage(`Imported ${m} member${m !== 1 ? 's' : ''} and ${x} expense${x !== 1 ? 's' : ''}.`);
          setStatus('success');
        }
      } catch (err) {
        setMessage(`Import failed: ${err.message}`);
        setStatus('error');
      }
    };
    reader.onerror = () => {
      setMessage('Failed to read file.');
      setStatus('error');
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="card">
      <h3>Import from JSON</h3>
      <p className="hint">Import members and expenses from a JSON file.</p>
      <label className="btn btn-secondary file-label">
        Choose JSON File
        <input type="file" accept=".json" onChange={handleFile} style={{ display: 'none' }} />
      </label>
      {message && (
        <pre className={`import-message ${status}`}>{message}</pre>
      )}
    </div>
  );
}