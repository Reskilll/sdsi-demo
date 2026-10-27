const API = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data?.error?.message || `Request failed (${res.status})`);
    err.code = data?.error?.code;
    err.status = res.status;
    throw err;
  }
  return data;
}

export function shorten(payload) {
  return request('/shorten', { method: 'POST', body: JSON.stringify(payload) });
}

export function fetchStats(code) {
  return request(`/stats/${encodeURIComponent(code)}`);
}
