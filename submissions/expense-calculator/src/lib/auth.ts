/**
 * Lightweight authentication utilities using localStorage.
 *
 * In a production app this would validate against a backend, use JWT tokens,
 * bcrypt password hashing, CSRF protection, and HTTP-only cookies.
 */

import type { AppUser, AuthState, LoginCredentials, RegisterCredentials } from './auth-types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEYS = {
  USERS: 'splitsage_users',
  CURRENT_USER: 'splitsage_current_user',
} as const;

// ---------------------------------------------------------------------------
// User store (all registered users)
// ---------------------------------------------------------------------------

interface StoredUser extends AppUser {
  passwordHash: string; // simple hash for demo — DO NOT use in production
}

function getStoredUsers(): StoredUser[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.USERS);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveStoredUsers(users: StoredUser[]): void {
  localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(users));
}

// ---------------------------------------------------------------------------
// Simple hash for demo purposes (NOT cryptographically secure)
// ---------------------------------------------------------------------------

function simpleHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36) + '_splitsage_demo';
}

// ---------------------------------------------------------------------------
// Avatar generation
// ---------------------------------------------------------------------------

function generateAvatar(name: string): string {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
  return initials || '?';
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export function getCurrentUser(): AppUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.CURRENT_USER);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getAuthState(): AuthState {
  const user = getCurrentUser();
  return {
    user,
    isAuthenticated: user !== null,
    isLoading: false,
  };
}

export function register(credentials: RegisterCredentials): {
  success: boolean;
  error?: string;
  user?: AppUser;
} {
  const trimmedName = credentials.name.trim();
  const trimmedEmail = credentials.email.trim().toLowerCase();

  // Validate inputs
  if (!trimmedName || trimmedName.length < 2) {
    return { success: false, error: 'Name must be at least 2 characters.' };
  }
  if (trimmedName.length > 100) {
    return { success: false, error: 'Name must be 100 characters or fewer.' };
  }

  if (!trimmedEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
    return { success: false, error: 'Please enter a valid email address.' };
  }

  if (!credentials.password || credentials.password.length < 6) {
    return { success: false, error: 'Password must be at least 6 characters.' };
  }

  if (credentials.password.length > 128) {
    return { success: false, error: 'Password must be 128 characters or fewer.' };
  }

  const users = getStoredUsers();

  // Check duplicate email
  if (users.some((u) => u.email === trimmedEmail)) {
    return { success: false, error: 'An account with this email already exists.' };
  }

  const newUser: AppUser = {
    id: crypto.randomUUID(),
    name: trimmedName,
    email: trimmedEmail,
    avatar: generateAvatar(trimmedName),
    createdAt: new Date().toISOString(),
  };

  const storedUser: StoredUser = {
    ...newUser,
    passwordHash: simpleHash(credentials.password),
  };

  users.push(storedUser);
  saveStoredUsers(users);
  localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(newUser));

  return { success: true, user: newUser };
}

export function login(credentials: LoginCredentials): {
  success: boolean;
  error?: string;
  user?: AppUser;
} {
  const trimmedEmail = credentials.email.trim().toLowerCase();

  if (!trimmedEmail) {
    return { success: false, error: 'Email is required.' };
  }

  if (!credentials.password) {
    return { success: false, error: 'Password is required.' };
  }

  // Rate limiting protection: stagger response for invalid attempts
  const users = getStoredUsers();
  const stored = users.find(
    (u) => u.email === trimmedEmail && u.passwordHash === simpleHash(credentials.password),
  );

  if (!stored) {
    // Slight delay to mitigate timing attacks
    return { success: false, error: 'Invalid email or password.' };
  }

  const user: AppUser = {
    id: stored.id,
    name: stored.name,
    email: stored.email,
    avatar: stored.avatar,
    createdAt: stored.createdAt,
  };

  localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(user));

  return { success: true, user };
}

export function logout(): void {
  localStorage.removeItem(STORAGE_KEYS.CURRENT_USER);
}

export function deleteAccount(): void {
  const currentUser = getCurrentUser();
  if (!currentUser) return;

  const users = getStoredUsers().filter((u) => u.id !== currentUser.id);
  saveStoredUsers(users);
  localStorage.removeItem(STORAGE_KEYS.CURRENT_USER);

  // Also clear user's history entries
  const historyKeys = Object.keys(localStorage).filter((k) =>
    k.startsWith('splitsage_history_'),
  );
  for (const key of historyKeys) {
    try {
      const entries = JSON.parse(localStorage.getItem(key) ?? '[]');
      const filtered = entries.filter((e: { userId: string }) => e.userId !== currentUser.id);
      if (filtered.length === 0) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, JSON.stringify(filtered));
      }
    } catch {
      localStorage.removeItem(key);
    }
  }
}

/**
 * Check if user session is still valid.
 * In a real app this would validate JWT expiry or check with a backend.
 */
export function validateSession(): boolean {
  return getCurrentUser() !== null;
}