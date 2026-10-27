import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';

export default function GroupDetailPage() {
  const { groupId } = useParams();
  const [group, setGroup] = useState(null);
  const [members, setMembers] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newMember, setNewMember] = useState('');

  const fetchAll = async () => {
    try {
      setError('');
      const [g, m, e, b] = await Promise.all([
        api.getGroup(groupId),
        api.listMembers(groupId),
        api.listExpenses(groupId),
        api.getBalances(groupId),
      ]);
      setGroup(g);
      setMembers(m);
      setExpenses(e);
      setBalances(b);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, [groupId]);

  const addMember = async (e) => {
    e.preventDefault();
    if (!newMember.trim()) return;
    try {
      await api.addMember(groupId, { name: newMember.trim() });
      setNewMember('');
      await fetchAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const removeMember = async (memberId) => {
    try {
      await api.removeMember(groupId, memberId);
      await fetchAll();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading...</div>;
  }

  if (!group) {
    return <div className="text-center py-12 text-red-500">Group not found</div>;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link to="/" className="text-sm text-indigo-600 hover:underline mb-1 block">
            &larr; All Groups
          </Link>
          <h1 className="text-2xl font-bold">{group.name}</h1>
          {group.description && (
            <p className="text-gray-500 text-sm">{group.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link
            to={`/groups/${groupId}/expenses/new`}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
          >
            + Add Expense
          </Link>
          <Link
            to={`/groups/${groupId}/expenses/batch`}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300"
          >
            Batch Upload
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Members */}
        <div>
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4">
            <h2 className="font-semibold text-gray-900 mb-3">
              Members ({members.length})
            </h2>
            <ul className="space-y-2 mb-4">
              {members.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span>{m.name}</span>
                  <button
                    onClick={() => removeMember(m.id)}
                    className="text-red-400 hover:text-red-600 text-xs"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={addMember} className="flex gap-2">
              <input
                type="text"
                placeholder="Add member..."
                value={newMember}
                onChange={(e) => setNewMember(e.target.value)}
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm"
              >
                Add
              </button>
            </form>
          </div>

          {/* Balances (M2) */}
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 mt-4">
            <h2 className="font-semibold text-gray-900 mb-3">Balances</h2>
            {balances.length === 0 ? (
              <p className="text-sm text-gray-400">No expenses yet.</p>
            ) : (
              <ul className="space-y-2">
                {balances.map((b) => (
                  <li
                    key={b.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{b.name}</span>
                    <span
                      className={`font-medium ${
                        parseFloat(b.balance) >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      ₹{parseFloat(b.balance).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Link
              to={`/groups/${groupId}/settlements`}
              className="block mt-3 text-sm text-indigo-600 hover:underline"
            >
              View settlements &rarr;
            </Link>
          </div>
        </div>

        {/* Expenses */}
        <div className="md:col-span-2">
          <h2 className="font-semibold text-gray-900 mb-3">
            Expenses ({expenses.length})
          </h2>
          {expenses.length === 0 ? (
            <p className="text-sm text-gray-400">
              No expenses yet. Add one to see splits.
            </p>
          ) : (
            <div className="space-y-3">
              {expenses.map((exp) => (
                <div
                  key={exp.id}
                  className="bg-white border border-gray-200 rounded-xl shadow-sm p-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {exp.description}
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Paid by {exp.payer_name} &middot;{' '}
                        {exp.split_type.toLowerCase()} split &middot;{' '}
                        {new Date(exp.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="font-semibold text-gray-900">
                      ₹{parseFloat(exp.amount).toFixed(2)}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {exp.shares.map((s) => (
                      <span
                        key={s.id}
                        className="text-xs px-2 py-0.5 bg-gray-100 rounded-full text-gray-600"
                      >
                        {members.find((m) => m.id === s.memberId)?.name || '?'}: ₹
                        {parseFloat(s.amount).toFixed(2)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}