/**
 * API client — fetches data from the Python backend.
 * All monetary values arrive as strings from the backend (Decimal).
 */

const API = {
  base: '/api',

  async get(path) {
    const res = await fetch(this.base + path);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async post(path, data) {
    const res = await fetch(this.base + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async del(path) {
    const res = await fetch(this.base + path, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  fetchGroup()       { return this.get('/group'); },
  fetchBalances()    { return this.get('/balances'); },
  fetchSettlements() { return this.get('/settlements'); },
  fetchMembers()     { return this.get('/members'); },
  fetchExpenses()    { return this.get('/expenses'); },

  addExpense(data)   { return this.post('/expenses', data); },
  addMember(data)    { return this.post('/members', data); },
  importBatch(data)  { return this.post('/import', data); },
  resetStore()       { return this.post('/reset', {}); },

  deleteExpense(id)  { return this.del('/expenses/' + id); },
  deleteMember(id)   { return this.del('/members/' + id); },
};

/**
 * Format a Decimal string as INR currency.
 */
function fmtINR(val) {
  const num = parseFloat(val);
  if (isNaN(num)) return '₹0.00';
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Get initials for an avatar.
 */
function getInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return parts.map(p => p[0].toUpperCase()).join('').slice(0, 2);
}

/**
 * Hash a string to a color for avatars.
 */
function avatarColor(str) {
  const colors = [
    '#e0e7ff','#fce7f3','#d1fae5','#fef3c7','#e0e7ff',
    '#dbeafe','#ede9fe','#fce7f3','#cffafe','#f3e8ff',
  ];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return { bg: colors[Math.abs(hash) % colors.length], color: '#1e3a5f' };
}

/**
 * Toast notification.
 */
function showToast(msg, type) {
  const container = document.querySelector('.toast-container') || (() => {
    const c = document.createElement('div');
    c.className = 'toast-container';
    document.body.appendChild(c);
    return c;
  })();
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 4000);
}