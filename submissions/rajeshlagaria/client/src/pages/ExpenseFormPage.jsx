import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

const SPLIT_TYPES = [
  { value: 'EQUAL', label: 'Equal' },
  { value: 'EXACT', label: 'Exact Amounts' },
  { value: 'PERCENTAGE', label: 'Percentage' },
];

function SumBadge({ label, sum, target, precision }) {
  if (target === undefined || target === null || target === 0) return null;
  const match = Math.abs(sum - target) < precision;
  return (
    <span
      className={`text-xs ml-2 px-2 py-0.5 rounded-full font-medium ${
        match ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      }`}
    >
      {label}: {sum.toFixed(2)}
      {!match && ` (need ${target.toFixed(2)})`}
    </span>
  );
}

export default function ExpenseFormPage() {
  const { groupId } = useParams();
  const navigate = useNavigate();

  const [members, setMembers] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [payerId, setPayerId] = useState('');
  const [splitType, setSplitType] = useState('EQUAL');
  const [shares, setShares] = useState([]);

  const exactSum = useMemo(() => {
    if (splitType !== 'EXACT') return null;
    return shares.reduce((acc, s) => acc + (parseFloat(s.amount) || 0), 0);
  }, [shares, splitType]);

  const pctSum = useMemo(() => {
    if (splitType !== 'PERCENTAGE') return null;
    return shares.reduce((acc, s) => acc + (parseFloat(s.percentage) || 0), 0);
  }, [shares, splitType]);

  useEffect(() => {
    api.listMembers(groupId).then(setMembers).catch(() => {});
  }, [groupId]);

  // Initialize shares when members load
  useEffect(() => {
    if (members.length > 0) {
      setShares(
        members.map((m) => ({
          memberId: m.id,
          amount: '',
          percentage: '',
          included: true,
        }))
      );
    }
  }, [members]);

  // Reset shares when split type changes
  useEffect(() => {
    if (members.length > 0) {
      setShares(
        members.map((m) => ({
          memberId: m.id,
          amount: '',
          percentage: '',
          included: splitType === 'EQUAL',
        }))
      );
    }
  }, [splitType, members.length]);

  const updateShare = (index, field, value) => {
    const updated = [...shares];
    updated[index] = { ...updated[index], [field]: value };
    setShares(updated);
  };

  const toggleMember = (index) => {
    const updated = [...shares];
    updated[index] = { ...updated[index], included: !updated[index].included };
    setShares(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Client-side pre-checks
    if (!payerId) {
      setError('Please select who paid.');
      return;
    }
    if (!amount || parseFloat(amount) <= 0) {
      setError('Amount must be a positive number.');
      return;
    }

    // Build payload
    let payloadShares;
    if (splitType === 'EQUAL') {
      const included = shares.filter((s) => s.included);
      if (included.length === 0) {
        setError('Select at least one member to split with.');
        return;
      }
      payloadShares = included.map((s) => ({ memberId: s.memberId }));
    } else if (splitType === 'EXACT') {
      payloadShares = shares.map((s) => ({
        memberId: s.memberId,
        amount: s.amount,
      }));
    } else {
      payloadShares = shares.map((s) => ({
        memberId: s.memberId,
        percentage: parseFloat(s.percentage) || 0,
      }));
    }

    try {
      setSubmitting(true);
      await api.createExpense(groupId, {
        payerId,
        description,
        amount: parseFloat(amount),
        splitType,
        shares: payloadShares,
      });
      navigate(`/groups/${groupId}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <button
        onClick={() => navigate(`/groups/${groupId}`)}
        className="text-sm text-indigo-600 hover:underline mb-4 block"
      >
        &larr; Back to Group
      </button>
      <h1 className="text-2xl font-bold mb-6">Add Expense</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl shadow-sm p-6"
      >
        {/* Description */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Dinner at Beach Shack"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        {/* Amount */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount (₹)
          </label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        {/* Payer */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Paid by
          </label>
          <select
            value={payerId}
            onChange={(e) => setPayerId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          >
            <option value="">Select payer...</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {/* Split type */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Split Type
          </label>
          <div className="flex gap-2">
            {SPLIT_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setSplitType(value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  splitType === value
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Shares */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Split Details
            <SumBadge
              label="Sum"
              sum={exactSum}
              target={parseFloat(amount) || 0}
              precision={0.01}
            />
            <SumBadge
              label="Total"
              sum={pctSum}
              target={100}
              precision={0.01}
            />
          </label>
          <div className="space-y-2">
            {shares.map((share, i) => {
              const member = members.find((m) => m.id === share.memberId);
              return (
                <div
                  key={share.memberId}
                  className="flex items-center gap-3 text-sm"
                >
                  {splitType === 'EQUAL' && (
                    <input
                      type="checkbox"
                      checked={share.included}
                      onChange={() => toggleMember(i)}
                      className="w-4 h-4 text-indigo-600"
                    />
                  )}
                  <span className="w-24 text-gray-700">{member?.name}</span>

                  {splitType === 'EXACT' && (
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={share.amount}
                      onChange={(e) => updateShare(i, 'amount', e.target.value)}
                      placeholder="₹0.00"
                      className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  )}

                  {splitType === 'PERCENTAGE' && (
                    <div className="flex items-center gap-1 flex-1">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="100"
                        value={share.percentage}
                        onChange={(e) =>
                          updateShare(i, 'percentage', e.target.value)
                        }
                        placeholder="0"
                        className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <span className="text-gray-400">%</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Saving...' : 'Save Expense'}
        </button>
      </form>
    </div>
  );
}