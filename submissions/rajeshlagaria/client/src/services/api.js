const BASE = '/api';

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `Request failed: ${res.status}`);
  }
  return data;
}

export const api = {
  // Groups
  createGroup: (body) =>
    request('/groups', { method: 'POST', body: JSON.stringify(body) }),
  listGroups: () => request('/groups'),
  getGroup: (id) => request(`/groups/${id}`),
  updateGroup: (id, body) =>
    request(`/groups/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteGroup: (id) => request(`/groups/${id}`, { method: 'DELETE' }),

  // Members
  addMember: (groupId, body) =>
    request(`/groups/${groupId}/members`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listMembers: (groupId) => request(`/groups/${groupId}/members`),
  removeMember: (groupId, memberId) =>
    request(`/groups/${groupId}/members/${memberId}`, { method: 'DELETE' }),

  // Expenses
  createExpense: (groupId, body) =>
    request(`/groups/${groupId}/expenses`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  batchCreateExpenses: (groupId, body) =>
    request(`/groups/${groupId}/expenses/batch`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listExpenses: (groupId) => request(`/groups/${groupId}/expenses`),
  getExpense: (groupId, expenseId) =>
    request(`/groups/${groupId}/expenses/${expenseId}`),
  deleteExpense: (groupId, expenseId) =>
    request(`/groups/${groupId}/expenses/${expenseId}`, { method: 'DELETE' }),

  // Balances & Settlements
  getBalances: (groupId) => request(`/groups/${groupId}/balances`),
  getSettlements: (groupId) => request(`/groups/${groupId}/settlements`),
};