import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

const SAMPLE_JSON = `{
  "expenses": [
    {
      "payerName": "Rajesh",
      "description": "Dinner at Fisherman's Wharf",
      "amount": 4000,
      "splitType": "EQUAL",
      "shares": [
        { "memberName": "Rajesh" },
        { "memberName": "Priya" },
        { "memberName": "Amit" },
        { "memberName": "Neha" }
      ]
    },
    {
      "payerName": "Priya",
      "description": "Taxi to beach",
      "amount": 1500,
      "splitType": "EXACT",
      "shares": [
        { "memberName": "Rajesh", "amount": 500 },
        { "memberName": "Priya", "amount": 500 },
        { "memberName": "Amit", "amount": 500 },
        { "memberName": "Neha", "amount": 0 }
      ]
    },
    {
      "payerName": "Amit",
      "description": "Groceries",
      "amount": 3000,
      "splitType": "PERCENTAGE",
      "shares": [
        { "memberName": "Rajesh", "percentage": 50 },
        { "memberName": "Priya", "percentage": 30 },
        { "memberName": "Amit", "percentage": 20 },
        { "memberName": "Neha", "percentage": 0 }
      ]
    }
  ]
}`;

export default function BatchUploadPage() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [jsonText, setJsonText] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadSample = () => setJsonText(SAMPLE_JSON);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    let parsed;
    try {
      parsed = JSON.parse(jsonText);
    } catch {
      setError('Invalid JSON. Please check the syntax.');
      return;
    }

    if (!parsed.expenses || !Array.isArray(parsed.expenses)) {
      setError('JSON must have an "expenses" array.');
      return;
    }

    if (parsed.expenses.length === 0) {
      setError('expenses array is empty.');
      return;
    }

    try {
      setSubmitting(true);
      const result = await api.batchCreateExpenses(groupId, parsed);
      setSuccess(
        `Successfully imported ${result.length} expense${result.length > 1 ? 's' : ''}.`
      );
      setJsonText('');
      setTimeout(() => navigate(`/groups/${groupId}`), 1500);
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
      <h1 className="text-2xl font-bold mb-6">Batch Upload Expenses</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
          {success}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl shadow-sm p-6"
      >
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Expenses JSON
          </label>
          <button
            type="button"
            onClick={loadSample}
            className="text-xs text-indigo-600 hover:underline"
          >
            Load sample
          </button>
        </div>
        <textarea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          rows={18}
          placeholder='Paste your JSON here...'
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
          required
        />
        <p className="text-xs text-gray-400 mt-2 mb-4">
          Use <code>payerName</code> or <code>payerId</code>, and <code>memberName</code> or{' '}
          <code>memberId</code> for each share. Split types: EQUAL, EXACT, PERCENTAGE.
        </p>
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Importing...' : 'Import Expenses'}
        </button>
      </form>
    </div>
  );
}