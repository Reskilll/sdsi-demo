import { useState, useRef } from 'react';
import './ExpenseForm.css';

export default function ExpenseForm({ members, memberMap, onSubmit, onCancel }) {
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [paidBy, setPaidBy] = useState('');
  const [splitType, setSplitType] = useState('equal');
  const [participants, setParticipants] = useState([]);
  const [exactAmounts, setExactAmounts] = useState({});
  const [percentages, setPercentages] = useState({});
  const [date, setDate] = useState('');
  const [errors, setErrors] = useState([]);
  const [showPreview, setShowPreview] = useState(false);
  const fileRef = useRef(null);

  const toggleParticipant = (id) => {
    setParticipants((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleExactAmount = (pid, value) => {
    setExactAmounts((prev) => ({ ...prev, [pid]: value }));
  };

  const handlePercentage = (pid, value) => {
    setPercentages((prev) => ({ ...prev, [pid]: value === '' ? '' : Number(value) }));
  };

  const resetForm = () => {
    setDescription('');
    setAmount('');
    setPaidBy('');
    setSplitType('equal');
    setParticipants([]);
    setExactAmounts({});
    setPercentages({});
    setDate('');
    setErrors([]);
    setShowPreview(false);
  };

  const validate = () => {
    const errs = [];
    if (!description.trim()) errs.push('Description is required.');
    const numAmount = Number(amount);
    if (!amount || !Number.isFinite(numAmount) || numAmount <= 0)
      errs.push('Amount must be a positive number.');
    if (!paidBy) errs.push('Please select a payer.');
    if (participants.length === 0) errs.push('Select at least one participant.');
    if (splitType === 'exact') {
      let sum = 0;
      for (const pid of participants) {
        const val = Number(exactAmounts[pid]);
        if (!Number.isFinite(val) || val < 0)
          errs.push(`Enter a valid non-negative amount for ${memberMap[pid] || pid}.`);
        else sum += Math.round(val * 100);
      }
      if (numAmount > 0 && sum !== Math.round(numAmount * 100))
        errs.push(`Exact amounts sum to ₹${(sum / 100).toFixed(2)}, expected ₹${numAmount.toFixed(2)}.`);
    }
    if (splitType === 'percentage') {
      let sum = 0;
      for (const pid of participants) {
        const val = Number(percentages[pid]);
        if (!Number.isFinite(val) || val < 0 || val > 100)
          errs.push(`Enter a valid percentage (0-100) for ${memberMap[pid] || pid}.`);
        else sum += val;
      }
      if (Math.abs(sum - 100) > 0.001)
        errs.push(`Percentages sum to ${sum.toFixed(2)}%, must total 100%.`);
    }
    if (date && isNaN(Date.parse(date))) errs.push('Invalid date.');
    return errs;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate();
    if (errs.length > 0) {
      setErrors(errs);
      return;
    }
    const input = {
      description: description.trim(),
      amount: Number(amount),
      paidBy,
      splitType,
      participants,
      exactAmounts: splitType === 'exact' ? { ...exactAmounts } : undefined,
      percentages: splitType === 'percentage' ? { ...percentages } : undefined,
      date: date || null,
    };
    const result = onSubmit(input);
    if (result && result.error) {
      setErrors([result.error]);
    } else {
      resetForm();
    }
  };

  const handleCancel = () => {
    resetForm();
    onCancel?.();
  };

  // Live share preview
  const previewShares = () => {
    if (!amount || Number(amount) <= 0 || participants.length === 0) return null;
    const totalPaise = Math.round(Number(amount) * 100);
    const shares = {};

    if (splitType === 'equal') {
      const base = Math.floor(totalPaise / participants.length);
      const rem = totalPaise - base * participants.length;
      const sorted = [...participants].sort();
      for (const pid of sorted) shares[pid] = base;
      for (let i = 0; i < rem; i++) shares[sorted[i]] += 1;
    } else if (splitType === 'exact') {
      for (const pid of participants) {
        const v = Number(exactAmounts[pid]) || 0;
        shares[pid] = Math.round(v * 100);
      }
    } else if (splitType === 'percentage') {
      for (const pid of participants) {
        const pct = Number(percentages[pid]) || 0;
        shares[pid] = Math.round((pct / 100) * totalPaise);
      }
    }
    return shares;
  };

  const preview = previewShares();

  return (
    <form className="expense-form" onSubmit={handleSubmit}>
      <h3>Add Expense</h3>

      {errors.length > 0 && (
        <div className="form-errors">
          {errors.map((e, i) => <p key={i}>{e}</p>)}
        </div>
      )}

      <div className="form-field">
        <label htmlFor="desc">Description</label>
        <input
          id="desc"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Dinner at Pind Balluchi"
        />
      </div>

      <div className="form-row">
        <div className="form-field">
          <label htmlFor="amount">Amount (₹)</label>
          <input
            id="amount"
            type="number"
            step="0.01"
            min="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="form-field">
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
      </div>

      <div className="form-field">
        <label htmlFor="payer">Paid by</label>
        <select id="payer" value={paidBy} onChange={(e) => setPaidBy(e.target.value)}>
          <option value="">Select payer</option>
          {members.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>

      <div className="form-field">
        <label>Split type</label>
        <div className="split-type-tabs">
          {['equal', 'exact', 'percentage'].map((t) => (
            <button
              key={t}
              type="button"
              className={`tab ${splitType === t ? 'active' : ''}`}
              onClick={() => setSplitType(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="form-field">
        <label>Participants</label>
        <div className="participant-chips">
          {members.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`chip ${participants.includes(m.id) ? 'selected' : ''}`}
              onClick={() => toggleParticipant(m.id)}
            >
              {m.name}
            </button>
          ))}
        </div>
      </div>

      {splitType === 'exact' && participants.length > 0 && (
        <div className="form-field">
          <label>Exact shares</label>
          <div className="split-inputs">
            {participants.map((pid) => (
              <div key={pid} className="split-input-row">
                <span>{memberMap[pid] || pid}</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={exactAmounts[pid] ?? ''}
                  onChange={(e) => handleExactAmount(pid, e.target.value)}
                  placeholder="0.00"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {splitType === 'percentage' && participants.length > 0 && (
        <div className="form-field">
          <label>Percentage shares</label>
          <div className="split-inputs">
            {participants.map((pid) => (
              <div key={pid} className="split-input-row">
                <span>{memberMap[pid] || pid}</span>
                <div className="pct-input-group">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="any"
                    value={percentages[pid] ?? ''}
                    onChange={(e) => handlePercentage(pid, e.target.value)}
                    placeholder="0"
                  />
                  <span>%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {preview && (
        <div className="preview-shares">
          <button type="button" className="preview-toggle" onClick={() => setShowPreview(!showPreview)}>
            {showPreview ? '▼' : '▶'} Preview shares
          </button>
          {showPreview && (
            <div className="preview-list">
              {Object.entries(preview).map(([pid, paise]) => (
                <div key={pid} className="preview-item">
                  <span>{memberMap[pid] || pid}</span>
                  <strong>₹{(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="form-actions">
        <button type="submit" className="btn btn-primary">Add Expense</button>
        <button type="button" className="btn btn-secondary" onClick={handleCancel}>Cancel</button>
      </div>
    </form>
  );
}