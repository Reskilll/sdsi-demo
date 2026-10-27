import { computed, reactive } from 'vue';
import { ApiError, onUnauthorized } from '../api/client';
import { roomsApi } from '../api/rooms';
import {
  clearSessionAuth,
  encodeBasicCredentials,
  loadSessionAuth,
  saveSessionAuth,
} from '../api/session';

interface AuthState {
  username: string;
  token: string;
  notice: string;
  busy: boolean;
}

const state = reactive<AuthState>({
  username: '',
  token: '',
  notice: '',
  busy: false,
});

let initialised = false;

function initialise(): void {
  if (initialised) return;
  initialised = true;

  const stored = loadSessionAuth();
  if (stored) {
    state.username = stored.username;
    state.token = stored.token;
  }

  onUnauthorized(() => {
    const hadSession = state.token !== '';
    clearSessionAuth();
    state.token = '';
    state.username = '';
    state.busy = false;
    if (hadSession) {
      state.notice = 'Your session has expired. Please sign in again.';
    }
  });
}

export interface LoginResult {
  ok: boolean;
  message?: string;
}

export function useAuth() {
  initialise();

  const isAuthenticated = computed(() => state.token !== '');
  const username = computed(() => state.username);
  const notice = computed(() => state.notice);
  const busy = computed(() => state.busy);

  async function login(candidateUsername: string, password: string): Promise<LoginResult> {
    const usernameValue = candidateUsername.trim();
    if (!usernameValue || !password) {
      return { ok: false, message: 'Enter both a username and a password.' };
    }

    state.busy = true;
    state.notice = '';
    const token = encodeBasicCredentials(usernameValue, password);
    try {
      await roomsApi.list(token);
      state.username = usernameValue;
      state.token = token;
      saveSessionAuth({ username: usernameValue, token });
      return { ok: true };
    } catch (error: unknown) {
      if (error instanceof ApiError) {
        if (error.status === 401 || error.status === 403) {
          return { ok: false, message: 'That username and password were not accepted.' };
        }
        return { ok: false, message: error.detail };
      }
      return {
        ok: false,
        message: 'Could not reach the booking service. Check that it is running and try again.',
      };
    } finally {
      state.busy = false;
    }
  }

  function logout(message = 'You have been signed out.'): void {
    clearSessionAuth();
    state.token = '';
    state.username = '';
    state.busy = false;
    state.notice = message;
  }

  function clearNotice(): void {
    state.notice = '';
  }

  return {
    isAuthenticated,
    username,
    notice,
    busy,
    login,
    logout,
    clearNotice,
  };
}
