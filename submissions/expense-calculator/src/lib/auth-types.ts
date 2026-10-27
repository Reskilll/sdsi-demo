/**
 * Auth context and types for the Expense Splitter.
 * Lightweight authentication using localStorage — no backend required.
 */

export interface AppUser {
  id: string;
  name: string;
  email: string;
  avatar: string;         // initial-based or URL
  createdAt: string;      // ISO
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials extends LoginCredentials {
  name: string;
}

export interface AuthState {
  user: AppUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface ExpenseHistoryEntry {
  id: string;
  timestamp: string;      // ISO
  action: 'create' | 'settle' | 'import' | 'clear' | 'reset';
  description: string;
  details?: string;       // extra info
  expenseCount: number;
  memberCount: number;
  totalAmount: number;
  userId: string;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;      // ms, default 4000
}