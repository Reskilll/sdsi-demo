import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export default function SettlementsPage() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [settlements, setSettlements] = useState([]);
  const [balances, setBalances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.getSettlements(groupId),
      api.getBalances(groupId),
    ])
      .then(([s, b]) => {
        setSettlements(s);
        setBalances(b);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [groupId]);

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Computing settlements...</div>;
  }

  return (
    <div>
      <button
        onClick={() => navigate(`/groups/${groupId}`)}
        className="text-sm text-indigo-600 hover:underline mb-4 block"
      >
        &larr; Back to Group
      </button>
      <h1 className="text-2xl font-bold mb-6">Settlements</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Balance summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {balances.map((b) => {
          const bal = parseFloat(b.balance);
          return (
            <div
              key={b.id}
              className={`p-4 rounded-xl border ${
                bal >= 0
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900">{b.name}</span>
                <span
                  className={`font-bold ${
                    bal >= 0 ? 'text-green-700' : 'text-red-700'
                  }`}
                >
                  {bal >= 0 ? '+' : ''}₹{bal.toFixed(2)}
                </span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Paid ₹{parseFloat(b.paid).toFixed(2)} &middot; Owes ₹
                {parseFloat(b.owed).toFixed(2)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Settlement instructions */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h2 className="font-semibold text-gray-900 mb-4">
          Simplified Payments ({settlements.length} transaction
          {settlements.length !== 1 ? 's' : ''})
        </h2>

        {settlements.length === 0 ? (
          <p className="text-sm text-gray-400">
            Everyone is settled up! No payments needed.
          </p>
        ) : (
          <ul className="space-y-3">
            {settlements.map((s, i) => (
              <li
                key={i}
                className="flex items-center gap-3 p-3 bg-indigo-50 rounded-lg"
              >
                <span className="font-medium text-gray-900">{s.from}</span>
                <span className="text-gray-400 text-sm">pays</span>
                <span className="font-medium text-gray-900">{s.to}</span>
                <span className="ml-auto font-bold text-indigo-700">
                  ₹{s.amount.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}