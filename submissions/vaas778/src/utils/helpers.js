/**
 * Generate a simple unique ID.
 * Uses crypto.randomUUID when available; falls back to timestamp + random.
 */
export function generateId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}

/** Deep-clone a JSON-serializable value. */
export function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

/** Group an array by a key function. Returns a Map. */
export function groupBy(arr, keyFn) {
  const map = new Map();
  for (const item of arr) {
    const key = keyFn(item);
    const existing = map.get(key);
    if (existing) {
      existing.push(item);
    } else {
      map.set(key, [item]);
    }
  }
  return map;
}