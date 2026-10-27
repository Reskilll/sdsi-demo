/** Session-scoped HTTP Basic credentials. Never touches localStorage. */

const STORAGE_KEY = 'booking.auth';

export interface StoredAuth {
  username: string;
  /** Base64 of `username:password`, sent as the Basic auth credential. */
  token: string;
}

function isStoredAuth(value: unknown): value is StoredAuth {
  if (typeof value !== 'object' || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.username === 'string' && typeof record.token === 'string';
}

export function encodeBasicCredentials(username: string, password: string): string {
  const bytes = new TextEncoder().encode(`${username}:${password}`);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function loadSessionAuth(): StoredAuth | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isStoredAuth(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function saveSessionAuth(auth: StoredAuth): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
  } catch {
    // Storage can be unavailable (private mode, policy). The app still works
    // for the lifetime of the tab because the reactive state holds the token.
  }
}

export function clearSessionAuth(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}
